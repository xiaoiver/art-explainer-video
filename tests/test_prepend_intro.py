"""Timing regressions for real intro + episode exports, without generated media calls."""
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('prepend_intro', Path(__file__).resolve().parents[1] / 'scripts/prepend_intro.py')
join = importlib.util.module_from_spec(spec)
spec.loader.exec_module(join)


def media(seconds, width=1920, height=1080, fps=24):
    return dict(duration=Fraction(str(seconds)), width=width, height=height, fps=Fraction(fps), audio=True)


class IntroTimingTests(unittest.TestCase):
    def test_american_gothic_observed_timeline_and_caption(self):
        p = join.plan_join(media(4), media(27.5, 1280, 720), 6)
        self.assertEqual(p['frames'], 750)
        self.assertEqual(p['duration'], Fraction(125, 4))
        self.assertEqual(p['offset'], Fraction(15, 4))
        text = '1\n00:00:03,458 --> 00:00:04,833\n拿把叉站半天，\n'
        self.assertEqual(join.shift_srt(text, p['offset']),
                         '1\n00:00:07,208 --> 00:00:08,583\n拿把叉站半天，\n')

    def test_short_intro_has_own_offset(self):
        p = join.plan_join(media(1.5), media(27.5), 6)
        self.assertEqual((p['offset'], p['duration'], p['frames']),
                         (Fraction(5, 4), Fraction(115, 4), 690))

    def test_cut_has_no_lost_frames(self):
        p = join.plan_join(media(4), media(27.5), 0)
        self.assertEqual((p['offset'], p['frames']), (4, 756))

    def test_portrait_is_not_silently_stretched(self):
        with self.assertRaises(ValueError):
            join.plan_join(media(4), media(27.5, 1080, 1920), 6)

    def test_overlap_cannot_consume_a_whole_input(self):
        for n in (-1, 96, 120):
            with self.subTest(frames=n), self.assertRaises(ValueError):
                join.plan_join(media(4), media(27.5), n)

    def test_subtitle_rollover_keeps_dialogue(self):
        self.assertEqual(join.shift_srt('00:59:59,900 --> 01:00:00,300\n前景。', Fraction(5, 4)),
                         '01:00:01,150 --> 01:00:01,550\n前景。')

    def test_invalid_subtitles_are_rejected(self):
        for s in ('no timestamps', '00:61:00,000 --> 00:61:02,000'):
            with self.subTest(text=s), self.assertRaises(ValueError):
                join.shift_srt(s, Fraction(1))


if __name__ == '__main__':
    unittest.main()
