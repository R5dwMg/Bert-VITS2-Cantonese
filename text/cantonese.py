import re
import unicodedata
import cn2an
import pinyin_jyutping
import pycantonese

from text.symbols import punctuation


def normalizer(x): return cn2an.transform(x, "an2cn")


j = pinyin_jyutping.PinyinJyutping()

INITIALS = [
    "aa",
    "aai",
    "aak",
    "aap",
    "aat",
    "aau",
    "ai",
    "au",
    "ap",
    "at",
    "ak",
    "a",
    "p",
    "b",
    "e",
    "ts",
    "t",
    "dz",
    "d",
    "kw",
    "k",
    "gw",
    "g",
    "f",
    "h",
    "l",
    "m",
    "ng",
    "n",
    "s",
    "y",
    "w",
    "c",
    "z",
    "j",
    "ong",
    "on",
    "ou",
    "oi",
    "ok",
    "o",
    "uk",
    "ung",
]


rep_map = {
    "￼": ",",
    "：": ",",
    "︰": ",",
    "；": ",",
    "，": ",",
    "。": ".",
    "！": "!",
    "？": "?",
    "﹖": "?",
    "﹗": "!",
    "\n": ".",
    "·": ",",
    "、": ",",
    "丶": ",",
    "...": "…",
    "⋯": "…",
    "$": ".",
    "“": "'",
    "”": "'",
    '"': "'",
    "‘": "'",
    "’": "'",
    "（": "'",
    "）": "'",
    "(": "'",
    ")": "'",
    "《": "'",
    "》": "'",
    "【": "'",
    "】": "'",
    "[": "'",
    "]": "'",
    "—": "-",
    "～": "-",
    "~": "-",
    "「": "'",
    "」": "'",
    "_": "-",
}

replacement_chars = {
    'ㄧ': '一',
    '—': '一',
    '更': '更',
    '不': '不',
    '料': '料',
    '聯': '聯',
    '行': '行',
    '利': '利',
    '謢': '護',
    '岀': '出',
    '鎭': '鎮',
    '戯': '戲',
    '旣': '既',
    '立': '立',
    '來': '來',
    '年': '年',
    '㗇': '蝦',
}


def replace_punctuation(text):
    # text = text.replace("嗯", "恩").replace("呣", "母")
    pattern = re.compile("|".join(re.escape(p) for p in rep_map.keys()))

    replaced_text = pattern.sub(lambda x: rep_map[x.group()], text)

    replaced_text = "".join(
        c for c in replaced_text if unicodedata.name(c, "").startswith("CJK UNIFIED IDEOGRAPH") or c in punctuation
    )

    return replaced_text


def replace_chars(text):
    for k, v in replacement_chars.items():
        text = text.replace(k, v)
    return text


def text_normalize(text):
    text = normalizer(text)
    text = replace_punctuation(text)
    text = replace_chars(text)
    return text


def jyuping_to_initials_finals_tones(jyuping_syllables):
    initials_finals = []
    tones = []
    word2ph = []

    for syllable in jyuping_syllables:
        if syllable in punctuation:
            initials_finals.append(syllable)
            tones.append(0)
            word2ph.append(1)  # Add 1 for punctuation
        else:
            try:
                tone = int(syllable[-1])
                syllable_without_tone = syllable[:-1]
            except ValueError:
                raise ValueError(f"Failed to convert {syllable}")

            assert str(
                tone) in "0123456", f"Failed to convert {syllable} with tone {tone}"

            for initial in INITIALS:
                if syllable_without_tone.startswith(initial):
                    if syllable_without_tone.startswith("nga"):
                        initials_finals.extend(
                            [
                                syllable_without_tone[:2],
                                syllable_without_tone[2:] or syllable_without_tone[-1],
                            ]
                        )
                        tones.extend([tone, tone])
                        word2ph.append(2)
                    else:
                        final = syllable_without_tone[len(
                            initial):] or initial[-1]
                        initials_finals.extend([initial, final])
                        tones.extend([tone, tone])
                        word2ph.append(2)
                    break
    assert len(initials_finals) == len(tones)
    return initials_finals, tones, word2ph


def get_jyutping(text):
    converted_text = j.jyutping(text, tone_numbers=True, spaces=True)
    converted_words = converted_text.split()

    for i, word in enumerate(converted_words):
        if set(word) <= set(text) - set(punctuation):
            converted_word = pycantonese.characters_to_jyutping(word)[0][1]
            converted_words[i] = converted_word

        if word not in punctuation and re.search(r'^[a-zA-Z]+[1-6]$', converted_words[i]) is None:
            raise ValueError(
                f"Failed to convert {converted_words[i]}, {converted_text}")

    jyutping_sentence = " ".join(converted_words)

    for symbol in punctuation:
        jyutping_sentence = jyutping_sentence.replace(
            symbol, " " + symbol + " ")
    jyutping_array = jyutping_sentence.split()

    return jyutping_array


def get_bert_feature(text, word2ph):
    from text import cantonese_bert

    return cantonese_bert.get_bert_feature(text, word2ph)


def g2p(text):
    word2ph = []
    jyuping = get_jyutping(text)
    phones, tones, word2ph = jyuping_to_initials_finals_tones(jyuping)
    phones = ["_"] + phones + ["_"]
    tones = [0] + tones + [0]
    word2ph = [1] + word2ph + [1]
    return phones, tones, word2ph


if __name__ == "__main__":
    from text.cantonese_bert import get_bert_feature

    # text = "你點解會咁柒㗎？我真係唔該晒你呀！"
    text = "佢哋最叻咪就係去㗇人傷害人,得個殼咋!"
    text = text_normalize(text)
    print(text)
    phones, tones, word2ph = g2p(text)
    bert = get_bert_feature(text, word2ph)

    print(phones, tones, word2ph, bert.shape)
