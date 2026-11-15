import unittest
from unittest import mock

from bot.langage import transcription_locale
from tests.test_voix import wav_sinus


class TestTranscriptionLocale(unittest.TestCase):
    def test_amorce_et_francais(self):
        modele = mock.Mock()
        modele.transcribe.return_value = ([mock.Mock(text=" Mon champ est "), mock.Mock(text="à Korhogo. ")], None)
        with mock.patch.object(transcription_locale, "_modele", return_value=modele):
            self.assertEqual(transcription_locale.transcrire(wav_sinus(1.0)), "Mon champ est à Korhogo.")
        signal = modele.transcribe.call_args.args[0]
        self.assertEqual(signal.dtype.name, "float32")
        self.assertAlmostEqual(len(signal) / 16000, 1.0, delta=0.05)
        self.assertEqual(modele.transcribe.call_args.kwargs["language"], "fr")
        self.assertIn("Korhogo", modele.transcribe.call_args.kwargs["initial_prompt"])

    def test_note_trop_longue(self):
        with mock.patch.object(transcription_locale, "_modele") as modele, self.assertRaises(ValueError):
            transcription_locale.transcrire(wav_sinus(121, taux=8000))
        modele.assert_not_called()


if __name__ == "__main__":
    unittest.main()
