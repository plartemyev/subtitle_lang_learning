#!/usr/bin/env python3

import argparse
import base64
import logging
import os
import zlib
import re
import nltk
from typing import List, Dict
from xmlrpc.client import ServerProxy, Transport

import srt

logger = logging.getLogger(__name__)
logging.captureWarnings(True)

language_codes = {
    'English': 'eng',
    'German': 'ger'
}

map_universal_to_wordnet = {
    'VERB': 'v',  # verbs
    'NOUN': 'n',  # nouns
    'PRON': 'n',  # pronouns
    'ADJ': 'a',  # adjectives
    'ADV': 'r',  # adverbs
    'ADP': 'r',  # adpositions (prepositions and postpositions)
    'CONJ': 's',  # conjunctions
    'DET': 's',  # determiners
    'NUM': 'n',  # cardinal numbers
    'PRT': 'n',  # particles or other function words
    'X': 'n',  # other: foreign words, typos, abbreviations
    '.': 'n',  # punctuation
}

html_tags_filter = re.compile(r'<.*?>')
www_spam_filter = re.compile(r'www\.\w+', re.I)

opensubtitles_api_url = 'http://api.opensubtitles.org/xml-rpc'
opensubtitles_ua = 'TemporaryUserAgent'
opensubtitles_lang = 'en'


class ModuleParameters:
    def __init__(self):
        cli = argparse.ArgumentParser()
        cli.add_argument('subtitle_file', type=str)
        cli.add_argument('--language', type=str, default='English')
        cli.add_argument('--debug', action='store_true')
        cli_args = cli.parse_args()
        self.subtitle: str = cli_args.subtitle_file
        self.language: str = cli_args.language
        self.debug: bool = cli_args.debug


class OpenSubtitles:
    def __init__(self):
        self.data = {}
        self.token = None
        self.xmlrpc_transport = Transport()
        self.xmlrpc_transport.user_agent = opensubtitles_ua
        self.xmlrpc = ServerProxy(opensubtitles_api_url, allow_none=True, transport=self.xmlrpc_transport)

    def _strengthened_get(self, key):
        status = self.data.get('status').split()[0] if isinstance(self.data.get('status'), str) else ''
        return self.data.get(key) if '200' == status else None

    def retrieve_subtitles(self, ids: List[str]) -> Dict[str, str]:
        self.data = self.xmlrpc.DownloadSubtitles(self.token, ids)
        subtitles_content = {}
        encoded_data = self._strengthened_get('data')
        for item in encoded_data:
            subfile_id = item['idsubtitlefile']

            try:
                decoded_data = decompress(item['data'], 'utf_8_sig') or decompress(item['data'], 'utf-8')
            except UnicodeDecodeError:
                decoded_data = decompress(item['data'], 'latin1')

            if not decoded_data:
                logger.error('An error occurred while decoding subtitle'
                                    'file ID {}.'.format(subfile_id))
            else:
                subtitles_content[subfile_id] = decoded_data
        return subtitles_content

    def search_subtitles(self, param: List[dict]) -> List[Dict[str, str]]:
        self.data = self.xmlrpc.SearchSubtitles(self.token, param)
        return self._strengthened_get('data')

    def login(self, username, password, lang, user_agent):
        self.data = self.xmlrpc.LogIn(username, password, lang, user_agent)
        token = self._strengthened_get('token')
        if token:
            self.token = token
        return token


def decompress(data, encoding):
    """
    Convert a base64-compressed subtitles file back to a string.

    :param data: the compressed data
    :param encoding: the encoding of the original file (e.g. utf-8, latin1)
    """
    try:
        return zlib.decompress(base64.b64decode(data),
                               16 + zlib.MAX_WBITS).decode(encoding)
    except UnicodeDecodeError as e:
        logger.info(f'Unable to decode content as {encoding}')
        logger.debug(e)
        raise


def logger_init():
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.handlers.append(console_handler)


def parse_subtitles(sub_gen: srt.parse) -> Dict[str, dict]:
    subs_dict = {}
    wordnet_lemmatizer = nltk.WordNetLemmatizer()
    for sub_object in sub_gen:
        sub_text = html_tags_filter.sub('', sub_object.content)
        if www_spam_filter.search(sub_text):
            # Skipping whole phrase as spam
            continue
        tagged_sub_tokens = nltk.pos_tag(nltk.word_tokenize(sub_text), tagset='universal')
        for tagged_token in tagged_sub_tokens:
            if tagged_token[1] in ('.', 'NUM'):
                # skipping punctuation and cardinal numbers
                continue
            word = ''
            if tagged_token[0].startswith("'") and tagged_token[1] == 'VERB':
                if tagged_token[0] == "'re":
                    word = 'are'
                elif tagged_token[0] == "'s":
                    word = 'is'
                elif tagged_token[0] == "'ve":
                    word = 'have'
            else:
                word = tagged_token[0]
            lemma = wordnet_lemmatizer.lemmatize(word, pos=map_universal_to_wordnet[tagged_token[1]]).lower()
            if lemma not in subs_dict.keys():
                subs_dict[lemma] = {'count': 1, 'sub_object': sub_object, 'sub_text': sub_text}
            else:
                subs_dict[lemma]['count'] += 1
    logger.info(f'Parsed {len(subs_dict)} unique words')
    return dict(sorted(subs_dict.items(), key=lambda _kv: _kv[1]['count'], reverse=True))


def read_subtitles_file(sub_file_path: str) -> str:
    logger.info(f'Reading file {sub_file_path}')
    with open(sub_file_path, encoding='latin-1') as sub_f:
        return sub_f.read()


def search_subtitles(video_name: str, language: str, ost_h: OpenSubtitles) -> List[Dict[str, str]]:
    logger.info(f'Searching subtitles for title {video_name} ({language}) in online DB')
    online_subs = ost_h.search_subtitles([{
        'sublanguageid': language_codes.get(language, 'eng'),
        'query': video_name
    }])
    logger.info(f'Found {len(online_subs)} matching subtitles')
    return online_subs


def download_subtitle(ost_h: OpenSubtitles, sub_id: str, sub_name: str) -> str:
    logger.info(f'Downloading subtitle file {sub_name} ID: {sub_id}')
    raw_subs_dict = ost_h.retrieve_subtitles([sub_id])
    return raw_subs_dict.get(sub_id)


if __name__ == '__main__':
    parameters = ModuleParameters()
    if parameters.debug:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('INFO')

    if parameters.subtitle.lower().endswith('.srt') and os.path.isfile(parameters.subtitle):
        raw_sub = read_subtitles_file(parameters.subtitle)
    else:
        ost_handle = OpenSubtitles()
        ost_handle.login('', '', opensubtitles_lang, opensubtitles_ua)
        online_subs_available = search_subtitles(parameters.subtitle, parameters.language, ost_handle)
        online_sub_id = online_subs_available[0].get('IDSubtitleFile')
        online_sub_name = online_subs_available[0].get('SubFileName')
        raw_sub = download_subtitle(ost_handle, online_sub_id, online_sub_name)
    sub_generator = srt.parse(raw_sub)
    sorted_subs_dict = parse_subtitles(sub_generator)
    for k, v in sorted_subs_dict.items():
        print(f'Word: {k} \t Count: {v["count"]}')
