import unittest
from datetime import date

from pipelines.gijiroku import ROW, Document, meeting_date, split_speaker, text


class ParseTest(unittest.TestCase):
    def test_row(self):
        row = (
            '<A HREF="voiweb.exe?ACT=100&KGTP=3&FYY=2025&TYY=2025&FINO=3053&PAGE=1&HIT=107"><IMG SRC="f.gif"></A>\n'
            "令和　７年１２月１０日議会運営委員会,<A HREF=\"javascript:;\" onClick=\"winopen('voiweb.exe?ACT=200"
            "&KGTP=3&KGNO=2034&FINO=3053&UNID=K_R07121015011');\">12月10日-01号</A>"
        )
        self.assertEqual(ROW.findall(row), [("3053", "令和　７年１２月１０日議会運営委員会", "2034", "12月10日-01号")])

    def test_meeting_date(self):
        d = Document(1, 2025, "3034", "2022", "令和　７年第４回定例会", "11月19日-26号")
        self.assertEqual(meeting_date(d), date(2025, 11, 19))
        d = Document(3, 2025, "3053", "2034", "令和　７年１２月１０日議会運営委員会", "目次")
        self.assertEqual(meeting_date(d), date(2025, 12, 10))

    def test_text_drops_cr(self):
        fragment = "○議長（木梨もりよし議員）　散会いたします。<BR>\r\n<BR>\r\n"
        self.assertEqual(split_speaker(text(fragment)), ("議長（木梨もりよし議員）", "散会いたします。"))

    def test_split_speaker(self):
        self.assertEqual(split_speaker("○議長（木梨もりよし議員）　これより開会します。"), ("議長（木梨もりよし議員）", "これより開会します。"))
        self.assertEqual(split_speaker("○石川ナオミ　議長　ただいまから開会します。", 2), ("石川ナオミ 議長", "ただいまから開会します。"))
        self.assertEqual(split_speaker("◆二十五番（中塚さちよ　議員）　冒頭、", 2), ("二十五番（中塚さちよ議員）", "冒頭、"))


if __name__ == "__main__":
    unittest.main()
