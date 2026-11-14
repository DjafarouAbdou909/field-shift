import io
import math
import struct
import unittest
import wave
from unittest import mock

import av

from bot.langage import voix


def wav_sinus(secondes=1.0, taux=24000):
    """WAV mono 16 bits d'un son de 440 Hz, comme la synthèse d'Aethex."""
    echantillons = [int(8000 * math.sin(2 * math.pi * 440 * i / taux)) for i in range(int(secondes * taux))]
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(taux)
        f.writeframes(struct.pack(f"<{len(echantillons)}h", *echantillons))
    return sortie.getvalue()


def duree_wav(contenu):
    with wave.open(io.BytesIO(contenu)) as f:
        return f.getnframes() / f.getframerate(), f.getnchannels(), f.getframerate()


class TestConversions(unittest.TestCase):
    def test_aller_retour_ogg_opus(self):
        """La synthèse WAV devient une note OGG Opus, qui redevient un WAV mono 16 kHz de même durée."""
        ogg = voix.vers_ogg_opus(wav_sinus(2.0))
        self.assertEqual(ogg[:4], b"OggS")
        with av.open(io.BytesIO(ogg)) as c:
            self.assertEqual(c.streams.audio[0].codec_context.name, "opus")
        duree, canaux, taux = duree_wav(voix.vers_wav(ogg))
        self.assertEqual((canaux, taux), (1, 16000))
        self.assertAlmostEqual(duree, 2.0, delta=0.1)

    def test_note_trop_longue_refusee(self):
        ogg = voix.vers_ogg_opus(wav_sinus(voix.DUREE_MAX_SECONDES + 1, taux=8000))
        with self.assertRaises(ValueError):
            voix.vers_wav(ogg)


class TestAethexSimule(unittest.TestCase):
    def setUp(self):
        voix._kora.cache_clear()
        voix.voix.cache_clear()
        self.kora = mock.Mock()
        self.patch = mock.patch.object(voix, "_kora", return_value=self.kora)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        voix.voix.cache_clear()

    def test_transcription_d_une_note_whatsapp(self):
        self.kora.transcribe.return_value = mock.Mock(text="  Je cultive du coton à Korhogo. ")
        texte = voix.transcrire(voix.vers_ogg_opus(wav_sinus(1.0)), "audio/ogg; codecs=opus")
        self.assertEqual(texte, "Je cultive du coton à Korhogo.")
        envoi = self.kora.transcribe.call_args
        self.assertEqual(envoi.kwargs["language"], "french")
        self.assertEqual(envoi.kwargs["mime_type"], "audio/wav")
        self.assertEqual(envoi.args[0][:4], b"RIFF")

    def test_transcription_vide(self):
        self.kora.transcribe.return_value = mock.Mock(text=None)
        self.assertEqual(voix.transcrire(wav_sinus(0.5), "audio/wav"), "")

    def test_synthese_en_ogg_opus_avec_voix_ivoirienne(self):
        self.kora.list_voices.return_value = [mock.Mock(id="voix-ci")]
        self.kora.synthesize_speech.return_value = wav_sinus(1.0)
        with mock.patch.dict("os.environ", {}, clear=True):
            note = voix.synthetiser("Bonjour")
        self.assertEqual(note[:4], b"OggS")
        self.kora.list_voices.assert_called_once_with(language="french", country="CI", limit=1)
        self.kora.synthesize_speech.assert_called_once_with("Bonjour", "voix-ci", language="french")

    def test_voix_fixee_par_l_environnement(self):
        with mock.patch.dict("os.environ", {"AETHEX_VOICE_ID": "voix-choisie"}):
            self.assertEqual(voix.voix(), "voix-choisie")
        self.kora.list_voices.assert_not_called()

    def test_sans_voix_francaise(self):
        self.kora.list_voices.return_value = []
        with mock.patch.dict("os.environ", {}, clear=True), self.assertRaises(RuntimeError):
            voix.synthetiser("Bonjour")


class TestSansCle(unittest.TestCase):
    def test_cle_absente(self):
        voix._kora.cache_clear()
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(voix.configuree())
            with self.assertRaises(RuntimeError):
                voix._kora()
        voix._kora.cache_clear()


if __name__ == "__main__":
    unittest.main()
