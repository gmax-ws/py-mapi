import re
import struct
from . import striprtf

RTF_MIME = re.compile(r".*\\from(html|text)", re.I)
RTF_CPG = re.compile(r".*\\ansicpg([0-9]+)", re.I)
HTML_RTF = re.compile(r"\\htmlrtf([0-1]?)", re.I)
RTF_WORD = re.compile(r"(\\[a-z0-9]+)", re.I)
RTF_ASCII = re.compile(r"\\'([0-9a-fA-F]{2})(.*)", re.I)
UNICODE = re.compile(r"\\u([0-9]{2,5})", re.I)
HTML_TAG = re.compile(r"{\\\*\\m?htmltag[0-9]+", re.I)

# Translation of some special characters.
SPECIAL_CHARS = {
    '\\par': '\n',
    '\\sect': '\n\n',
    '\\page': '\n\n',
    '\\line': '\n',
    '\\tab': '\t',
    '\\emdash': '&#2014;',
    '\\endash': '&#2013;',
    '\\emspace': '&#2003;',
    '\\enspace': '&#2002;',
    '\\qmspace': '&#2005;',
    '\\bullet': '&#2022;',
    '\\lquote': '&#2018;',
    '\\rquote': '&#2019;',
    '\\ldblquote': '&#201C;',
    '\\rdblquote': '&#201D;',
    '\\row': '\n',
    '\\cell': '|',
    '\\nestcell': '|'
}


class RtfHtml:
    __slots__ = ['tags', 'encoding']

    def __init__(self, encoding):
        self.encoding = encoding
        self.tags = []

    def export(self, rtf, decode_html=True):
        lines = re.split(HTML_TAG, rtf)
        for i in range(1, len(lines)):
            tag = self.process_line(lines[i])
            self.tags.append(self.make_html(tag, decode_html))
        return "".join(self.substitute(tag) for tag in self.tags).strip()

    def process_line(self, line):
        word, words = [], []
        for c in line:
            n = len(word)
            if c.isspace():
                if n != 0:
                    words.append("".join(word))
                words.append(c)
                word.clear()
            elif c == "\\":
                if n != 0:
                    words.append("".join(word))
                word.clear()
                word.append(c)
            elif c in ("{", "}"):
                if n != 0:
                    if word[-1] == "\\":
                        word[-1] = c
                    else:
                        words.append("".join(word))
                        word.clear()
            else:
                word.append(c)

        words.append("".join(word))
        return [self.substitute(w) for w in words]

    def substitute(self, word):
        spec_char = SPECIAL_CHARS.get(word, None)
        if spec_char is None:
            return self.regex_substitute(word)
        else:
            return spec_char

    def regex_substitute(self, word):
        match = RTF_ASCII.match(word)
        if match:
            v = match.groups()
            x = struct.pack("B", int(v[0], 16))
            return "%s%s" % (x.decode(self.encoding), v[1])

        match = UNICODE.match(word)
        if match:
            v = match.groups()
            return "&#%s;" % v[0]

        return word

    @staticmethod
    def make_html(words, toggle):
        text = []
        for i in range(0, len(words)):
            match = HTML_RTF.match(words[i])
            if match:
                toggle = match.groups()[0] == '0'
            elif toggle:
                if RTF_WORD.match(words[i]):
                    subst = SPECIAL_CHARS.get(words[i], None)
                    if subst is not None:
                        text.append(subst)
                else:
                    text.append(words[i])

        return "".join(text)


class RtfParser(RtfHtml):
    __slots__ = ['rtf', 'mime', 'encoding']

    def __init__(self, rtf):
        self.rtf = rtf
        self.mime = self._mime()
        self.encoding = self._cpg()
        super().__init__(self.encoding)

    def is_valid(self):
        return self.mime is not None

    def is_html(self):
        return self.mime == "html"

    def decode_html(self):
        if self.is_html():
            return self.export(self.rtf)
        else:
            raise Exception("No HTML content! (mime: %s)" % self.mime)

    def decode_text(self):
        return striprtf.rtf_to_text(self.rtf)

    def _mime(self):
        return self._regex(RTF_MIME)

    def _cpg(self):
        return self._regex(RTF_CPG)

    def _regex(self, pattern):
        match = pattern.match(self.rtf)
        return match.groups()[0] if match else None
