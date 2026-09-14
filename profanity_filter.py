import re
import os
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LEET_MAP = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a', '$': 's'
})

def load_banned_words(filepath=None):
    filepath = filepath or os.path.join(BASE_DIR, 'banned_words.txt')
    with open(filepath, 'r', encoding='utf-8') as f:
        return set(line.strip().lower() for line in f if line.strip() and not line.startswith('#'))


def normalize_word(word):
    word = word.lower()
    word = word.translate(LEET_MAP)
    word = re.sub(r'[^a-z0-9]', '', word)
    word = re.sub(r'(.)\1+', r'\1', word)
    return word

def stem(word):
    stemmed = re.sub(r'[aeiou]+$', '', word)
    return stemmed if len(stemmed) >= 3 else word

def _join_short_tokens(tokens):
    """Sirf spaced-out evasion pakadne ke liye: consecutive 1-2 letter
    tokens ko jodta hai (e.g. 'r a n d i' -> 'randi'), lekin normal
    lambi sentence ke words ko aapas mein nahi jodta."""
    joined_runs = []
    current_run = ""
    for tok in tokens:
        if len(tok) <= 2:
            current_run += tok
        else:
            if current_run:
                joined_runs.append(current_run)
                current_run = ""
    if current_run:
        joined_runs.append(current_run)
    return joined_runs

def contains_abuse(text):
    banned_words = load_banned_words()
    raw_tokens = re.findall(r'[a-zA-Z0-9@$]+', text.lower())
    norm_tokens = [normalize_word(t) for t in raw_tokens if t]

    single_words = {w for w in banned_words if ' ' not in w}
    phrase_words = {w for w in banned_words if ' ' in w}

    banned_norm = {normalize_word(w) for w in single_words}
    banned_stems = {stem(normalize_word(w)) for w in single_words}

    for tok in norm_tokens:
        if tok in banned_norm:
            return True
        if stem(tok) in banned_stems:
            return True

    for n in(2, 3):
        for i in range(len(norm_tokens) - n + 1):
            combo = ''.join(norm_tokens[i:i+n])
            if combo in banned_norm:
                return True

    normalized_sentence = ' '.join(norm_tokens)
    for phrase in phrase_words:
        phrase_clean = normalize_word(phrase.replace(' ', ''))
        if phrase_clean in normalized_sentence:
            return True

    joined_runs = _join_short_tokens(norm_tokens)
    for run in joined_runs:
        for word in banned_norm:
            if word in run:
                return True

    return False