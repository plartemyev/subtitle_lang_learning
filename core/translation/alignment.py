"""Cross-attention to word alignment for offline translation.

CTranslate2 returns, in the same decoding pass as the translation itself,
one attention vector per generated target token over all source tokens
(``return_attention=True``). These helpers turn that soft matrix into a
per-source-word translation map: special-token columns are dropped, target
SentencePiece pieces are merged into words, source pieces are mapped to the
spaCy tokens of the phrase via character offsets, and every target word
votes for its best source word. Attention is a hint, not ground truth
(Ferrando et al. 2021): below the confidence threshold a word gets no
translation and the UI can fall back to the dictionary gloss.
"""

SENTINEL_PIECE = '▁'  # SentencePiece marker: the piece starts a new word
# NLLB cross-attention is diffuse (an EOS sink swallows most of the mass),
# so even a "confident" vote is often misaligned; the dictionary layer is
# the primary per-word source and this fallback line stays honest only when
# the best target word holds at least half of the word's attention mass.
CONFIDENCE_THRESHOLD = 0.5


def drop_special_columns(vectors, keep_mask):
    """Restrict every attention vector to the real-text source positions.

    ``keep_mask`` marks, per source token of the model input, whether it is
    a real text token (language-code and end-of-sequence sentinels are not).
    """
    return [[mass for mass, keep in zip(vector, keep_mask) if keep]
            for vector in vectors]


def group_source_pieces(piece_offsets, words):
    """Map each source piece to the index of the spaCy word containing it.

    ``piece_offsets`` are (start, end) character offsets of the non-special
    source pieces within the phrase text, ``words`` the spaCy tokens with
    their (start, end) offsets. Both sides are ordered; a single sweep
    assigns each piece to the first word whose span overlaps it, or None
    for pieces outside every word span.
    """
    assignments = []
    word_index = 0
    for start, end in piece_offsets:
        while word_index < len(words) and words[word_index].end <= start:
            word_index += 1
        if (word_index < len(words) and start < words[word_index].end
                and end > words[word_index].start):
            assignments.append(word_index)
        else:
            assignments.append(None)
    return assignments


def merge_target_pieces(tokens, vectors):
    """Merge SentencePiece target pieces into words, summing their attention.

    ``tokens`` are the generated piece strings without special tokens,
    ``vectors`` the parallel attention rows over the already filtered source
    pieces. A new word starts at the ``▁`` sentinel and at punctuation
    pieces (SentencePiece glues '.', '?' onto the preceding word, but they
    must stay separate rows so they can be masked from the votes). Returns
    ``(word_text, summed_vector)`` pairs in generation order.
    """
    words = []
    current_text = ''
    current_vector = None
    for token, vector in zip(tokens, vectors):
        body = token[len(SENTINEL_PIECE):] if token.startswith(SENTINEL_PIECE) else token
        if token.startswith(SENTINEL_PIECE) or not current_text or is_punctuation(body):
            if current_text:
                words.append((current_text, current_vector))
            current_text = body
            current_vector = list(vector)
        else:
            current_text += body
            current_vector = [total + part for total, part in zip(current_vector, vector)]
    if current_text:
        words.append((current_text, current_vector))
    return words


def is_punctuation(text):
    """True for words made purely of punctuation/symbols (no letter or digit)."""
    return not any(char.isalnum() for char in text)


def pick_target_words(target_word_vectors, piece_to_word, source_word_count,
                      content_mask, threshold=CONFIDENCE_THRESHOLD):
    """For every source word, pick its strongest target word.

    ``target_word_vectors`` hold attention over the source pieces (special
    columns already dropped), ``piece_to_word`` maps piece index to source
    word index, ``content_mask`` marks target words eligible as votes
    (target-side punctuation is masked out: its attention is context noise,
    not a translation). Returns ``(target_word_index, confidence)`` per
    source word, ``(None, None)`` when the best candidate stays under
    ``threshold`` or nothing attaches to the word at all.
    """
    columns = [[0.0] * len(target_word_vectors) for _ in range(source_word_count)]
    for target_index, vector in enumerate(target_word_vectors):
        if not content_mask[target_index]:
            continue
        for piece_index, mass in enumerate(vector):
            word_index = piece_to_word[piece_index]
            if word_index is not None:
                columns[word_index][target_index] += mass
    votes = []
    for column in columns:
        total = sum(column)
        best_target = None
        best_score = 0.0
        for target_index, score in enumerate(column):
            if score > best_score:
                best_target = target_index
                best_score = score
        confidence = best_score / total if total > 0 else 0.0
        if best_target is None or confidence < threshold:
            votes.append((None, None))
        else:
            votes.append((best_target, confidence))
    return votes
