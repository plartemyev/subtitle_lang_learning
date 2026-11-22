#!/usr/bin/env python3

import argparse
import base64
import html
import logging
import os
import zlib
import re
import spacy
from typing import List, Dict
from xmlrpc.client import ServerProxy, Transport
from chardet.universaldetector import UniversalDetector

import srt

logger = logging.getLogger(__name__)
logging.captureWarnings(True)

language_codes = {
    'English': 'eng',
    'German': 'ger',
    'Russian': 'rus'
}

spacy_models = {
    'English': 'en_core_web_sm',
    'German': 'de_core_news_sm',
    'Russian': 'ru_core_news_sm'
}
_nlp_cache = {}

html_tags_filter = re.compile(r'<.*?>')
whitespace_filter = re.compile(r'[^\S\n]+')
www_spam_filter = re.compile(r'www\.\w+', re.I)


class ModuleParameters:
    def __init__(self, subtitle='', language='', debug=False):
        self.subtitle = subtitle
        self.language = language
        self.debug = debug


class OpenSubtitles:
    def __init__(self):
        # noinspection SpellCheckingInspection
        opensubtitles_ua = b'VkxzdWIgMC4xMC4y'
        self.ua = base64.b64decode(opensubtitles_ua).decode()
        self.opensubtitles_api_url = 'http://api.opensubtitles.org/xml-rpc'
        self.opensubtitles_lang = 'en'
        self.token = None
        self.xmlrpc_transport = Transport()
        self.xmlrpc_transport.user_agent = self.ua
        self.xmlrpc = ServerProxy(self.opensubtitles_api_url, allow_none=True, transport=self.xmlrpc_transport)

    def retrieve_subtitles(self, ids: List[str]) -> Dict[str, str]:
        response = self.xmlrpc.DownloadSubtitles(self.token, ids)
        status = response.get('status', '').split()[0]
        if status == '200':
            subtitles_content = {}
            encoded_data = response.get('data')
            for item in encoded_data:
                sub_id = item['idsubtitlefile']
                decoded_data = decompress(item['data'])
                if not decoded_data:
                    logger.error('An error occurred while decoding subtitle ID {}.'.format(sub_id))
                else:
                    subtitles_content[sub_id] = decoded_data
                return subtitles_content
        else:
            raise RuntimeWarning(f'Unable to get subtitles, returned status is {status}')

    def search_subtitles(self, param: List[dict]) -> List[Dict[str, str]]:
        response = self.xmlrpc.SearchSubtitles(self.token, param)
        status = response.get('status', '').split()[0]
        if status == '200':
            return response.get('data')
        else:
            raise RuntimeWarning(f'Unable to search subtitles, returned status is {status}')

    def login(self, username, password):
        response = self.xmlrpc.LogIn(username, password, self.opensubtitles_lang, self.ua)
        status = response.get('status', '').split()[0]
        if status == '200':
            self.token = response.get('token')
        else:
            raise RuntimeWarning(f'Unable to authenticate, returned status is {status}')


def decompress(data: bytes) -> str:
    """
    Convert a base64-compressed subtitles file back to a string.

    :param data: the compressed data
    """
    fall_back_encodings = ['utf_8_sig', 'utf-8', 'latin1']
    uncompressed_string = zlib.decompress(base64.b64decode(data), 16 + zlib.MAX_WBITS)
    detector = UniversalDetector()
    detector.feed(uncompressed_string)
    detector.close()
    encoding = detector.result.get('encoding')
    logger.debug(f"Detected encoding: {encoding}")
    try:
        decoded_string = uncompressed_string.decode(encoding=encoding)
    except (TypeError, UnicodeDecodeError):
        # Detection was inconclusive, trying fall-back encodings
        for encoding in fall_back_encodings:
            try:
                decoded_string = uncompressed_string.decode(encoding=encoding)
            except UnicodeDecodeError as e:
                logger.info(f'Unable to decode content as {encoding}')
                logger.debug(e)
            else:
                # No exceptions happened, decoding success
                break
        else:
            # Tried all fall-back encodings, no success
            raise RuntimeError('Unable to decode subtitle content')
    return decoded_string


def logger_init():
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.handlers.append(console_handler)


def get_nlp(language: str):
    model_name = spacy_models.get(language, 'en_core_web_sm')
    if model_name not in _nlp_cache:
        _nlp_cache[model_name] = spacy.load(model_name, exclude=['parser', 'ner'])
    return _nlp_cache[model_name]


def normalize_lemma(token) -> str:
    return token.lemma_.strip('-').lstrip('.').lower()


def annotate_phrase(doc) -> Dict:
    """Result of the single spaCy pass over a phrase, kept for UI rendering and word lookups."""
    return {'text': doc.text,
            'words': [{'text': token.text, 'lemma': normalize_lemma(token), 'pos': token.pos_,
                       'start': token.idx, 'end': token.idx + len(token.text)}
                      for token in doc if not token.is_space]}


def parse_subtitles(sub_gen: srt.parse, language: str = 'English', use_lemmas: bool = True) -> Dict[str, dict]:
    subs_dict = {}
    sub_texts = []
    sub_objects = []
    for sub_object in sub_gen:
        # strip tags first, so escaped literals like &lt;b&gt; survive as visible text
        sub_text = whitespace_filter.sub(
            ' ', html.unescape(html_tags_filter.sub('', sub_object.content))).strip()
        if www_spam_filter.search(sub_text):
            # Skipping whole phrase as spam
            continue
        sub_texts.append(sub_text)
        sub_objects.append(sub_object)
    unique_texts = list(dict.fromkeys(sub_texts))
    docs_by_text = {}
    for text, doc in zip(unique_texts, get_nlp(language).pipe(unique_texts, batch_size=64)):
        docs_by_text[text] = (doc, annotate_phrase(doc))
    for sub_object, sub_text in zip(sub_objects, sub_texts):
        doc, annotation = docs_by_text[sub_text]
        sub_object.sub_text_annotated = annotation
        for token in doc:
            if token.is_punct or token.is_space:
                continue
            word = normalize_lemma(token) if use_lemmas else token.lower_
            if token.tag_ == 'POS':
                # possessive marker: annotate the possessor's entry instead of a standalone word
                possessor_word = ''
                if token.i > 0:
                    possessor = doc[token.i - 1]
                    possessor_word = normalize_lemma(possessor) if use_lemmas else possessor.lower_
                if possessor_word in subs_dict.keys():
                    subs_dict[possessor_word]['possessive'] = subs_dict[possessor_word].get('possessive', 0) + 1
                continue
            if not word or token.is_digit or "'" in word:
                continue
            if word not in subs_dict.keys():
                subs_dict[word] = {'count': 1, 'pos': token.pos_, 'pos_counts': {token.pos_: 1},
                                    'occurrences': {token.pos_: [{'sub_object': sub_object, 'sub_text': sub_text}]},
                                    'sub_object': sub_object, 'sub_text': sub_text}
            else:
                entry = subs_dict[word]
                entry['count'] += 1
                entry['pos_counts'][token.pos_] = entry['pos_counts'].get(token.pos_, 0) + 1
                entry['occurrences'].setdefault(token.pos_, []).append(
                    {'sub_object': sub_object, 'sub_text': sub_text})
                if entry['pos_counts'][token.pos_] > entry['pos_counts'][entry['pos']]:
                    # keeping the most frequent part of speech in the entry meta
                    entry['pos'] = token.pos_
    logger.info(f'Parsed {len(subs_dict)} unique words')
    return dict(sorted(subs_dict.items(), key=lambda _kv: _kv[1]['count'], reverse=True))


def read_subtitles_file(sub_file_path: str) -> str:
    logger.info(f'Reading file {sub_file_path}')
    detector = UniversalDetector()
    for line in open(sub_file_path, mode='rb'):
        detector.feed(line)
        if detector.done:
            break
    detector.close()
    encoding = detector.result.get('encoding')
    if not encoding:
        raise RuntimeError(f'Unable to detect encoding for file {sub_file_path}')
    with open(sub_file_path, encoding=encoding) as sub_f:
        return sub_f.read()


def search_subtitles(video_name: str, language: str, ost_h: OpenSubtitles) -> List[Dict[str, str]]:
    logger.info(f'Searching subtitles for title {video_name} ({language}) in online DB')
    if online_subs := ost_h.search_subtitles([{
        'sublanguageid': language_codes.get(language, 'eng'),
        'query': video_name
    }]):
        logger.info(f'Found {len(online_subs)} matching subtitles')
        return online_subs
    else:
        return []


def download_subtitle(ost_h: OpenSubtitles, sub_id: str, sub_name: str) -> str:
    logger.info(f'Downloading subtitle file {sub_name} ID: {sub_id}')
    raw_subs_dict = ost_h.retrieve_subtitles([sub_id])
    return raw_subs_dict.get(sub_id)


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('subtitle_file', type=str)
    cli.add_argument('--language', type=str, default='English')
    cli.add_argument('--debug', action='store_true')
    cli_args = cli.parse_args()
    parameters = ModuleParameters(cli_args.subtitle_file, cli_args.language, cli_args.debug)

    if parameters.debug:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('INFO')

    if parameters.subtitle.lower().endswith('.srt') and os.path.isfile(parameters.subtitle):
        raw_sub = read_subtitles_file(parameters.subtitle)
    else:
        ost_handle = OpenSubtitles()
        ost_handle.login('', '')
        online_subs_available = search_subtitles(parameters.subtitle, parameters.language, ost_handle)
        online_sub_id = online_subs_available[0].get('IDSubtitleFile')
        online_sub_name = online_subs_available[0].get('SubFileName')
        raw_sub = download_subtitle(ost_handle, online_sub_id, online_sub_name)
    sub_generator = srt.parse(raw_sub)
    sorted_subs_dict = parse_subtitles(sub_generator, parameters.language)
    for k, v in sorted_subs_dict.items():
        print(f'Word: {k} \t Count: {v["count"]}')
