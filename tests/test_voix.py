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


class TestTextesLongs(unittest.TestCase):
    def test_decoupage_aux_fins_de_phrase(self):
        texte = " ".join(f"Phrase numéro {i} du résumé agricole." for i in range(60))
        parties = voix.morceaux(texte, 600)
        self.assertGreater(len(parties), 1)
        self.assertTrue(all(len(p) <= 600 for p in parties))
        self.assertTrue(all(p.endswith(".") for p in parties))
        self.assertEqual(" ".join(parties), texte)

    def test_phrase_sans_fin_coupee_aux_espaces(self):
        parties = voix.morceaux("mot " * 400, 600)
        self.assertTrue(all(len(p) <= 600 for p in parties))

    def test_synthese_gardee_en_memoire(self):
        kora = mock.Mock()
        kora.synthesize_speech.return_value = wav_sinus(0.5)
        voix.synthetiser.cache_clear()
        with mock.patch.object(voix, "_kora", return_value=kora), mock.patch.dict("os.environ", {"AETHEX_VOICE_ID": "v"}):
            voix.voix.cache_clear()
            premiere = voix.synthetiser("Que voulez-vous faire ?")
            seconde = voix.synthetiser("Que voulez-vous faire ?")
        voix.voix.cache_clear()
        voix.synthetiser.cache_clear()
        self.assertEqual(premiere, seconde)
        self.assertEqual(kora.synthesize_speech.call_count, 1)

    def test_morceaux_recolles_dans_l_ordre(self):
        """Synthétisés en parallèle, les morceaux gardent l'ordre du texte."""
        durees = {}

        def synthese(morceau, identifiant, language):
            rang = int(morceau.split()[1])
            durees[rang] = 0.2 + rang * 0.1
            return wav_sinus(durees[rang])
        kora = mock.Mock()
        kora.synthesize_speech.side_effect = synthese
        texte = " ".join(f"Morceau {i} " + "x" * 570 + "." for i in range(3))
        voix.synthetiser.cache_clear()
        with mock.patch.object(voix, "_kora", return_value=kora), mock.patch.dict("os.environ", {"AETHEX_VOICE_ID": "v"}), \
                mock.patch.object(voix, "vers_ogg_opus", side_effect=lambda *wavs: wavs) as encoder:
            voix.voix.cache_clear()
            wavs = voix.synthetiser(texte)
        voix.voix.cache_clear()
        voix.synthetiser.cache_clear()
        self.assertEqual(wavs, tuple(wav_sinus(durees[i]) for i in range(3)))

    def test_une_seule_note_pour_plusieurs_morceaux(self):
        kora = mock.Mock()
        kora.synthesize_speech.return_value = wav_sinus(1.0)
        voix.synthetiser.cache_clear()
        with mock.patch.object(voix, "_kora", return_value=kora), \
                mock.patch.dict("os.environ", {"AETHEX_VOICE_ID": "v"}):
            voix.voix.cache_clear()
            note = voix.synthetiser("Une phrase assez longue. " * 60)
        voix.voix.cache_clear()
        self.assertGreater(kora.synthesize_speech.call_count, 1)
        self.assertTrue(all(len(c.args[0]) <= 600 for c in kora.synthesize_speech.call_args_list))
        with av.open(io.BytesIO(note)) as c:
            duree = float(c.duration) / 1e6
        self.assertAlmostEqual(duree, kora.synthesize_speech.call_count * 1.0, delta=0.3)


class TestCreditsEpuises(unittest.TestCase):
    def tearDown(self):
        voix._en_pause_jusqua = 0.0
        voix.voix.cache_clear()
        voix.synthetiser.cache_clear()

    def test_pause_apres_refus_de_paiement(self):
        erreur = RuntimeError("You're out of credits. Add credits to keep making calls.")
        erreur.status_code = 402
        kora = mock.Mock()
        kora.synthesize_speech.side_effect = erreur
        voix.synthetiser.cache_clear()
        with mock.patch.object(voix, "_kora", return_value=kora), \
                mock.patch.dict("os.environ", {"AETHEX_VOICE_ID": "v", "AETHEX_API_KEY": "k"}):
            voix.voix.cache_clear()
            self.assertTrue(voix.configuree())
            with self.assertRaises(RuntimeError):
                voix.synthetiser("Bonjour")
            self.assertFalse(voix.configuree(), "Aethex est mis en pause, le bot répond par écrit sans attendre")
