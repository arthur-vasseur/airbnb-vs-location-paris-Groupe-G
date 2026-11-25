"""Tests du module fiscal, à partir des exemples de la brochure officielle IR 2026.

Lancement : python -m unittest test_fiscalite
"""

import unittest

from fiscalite import Bien, Foyer, _bareme, imposer, impot_revenu


class TestImpotRevenu(unittest.TestCase):
    def test_parts(self):
        self.assertEqual(Foyer().parts, 1)
        self.assertEqual(Foyer(couple=True, enfants=2).parts, 3)
        self.assertEqual(Foyer(couple=True, enfants=3).parts, 4)
        self.assertEqual(Foyer(enfants=1, parent_isole=True).parts, 2)

    def test_exemple_brochure_3_parts(self):
        # Brochure IR 2026 : couple avec 2 enfants, 54 000 € → impôt brut 2 112 €.
        self.assertAlmostEqual(_bareme(54_000, 3), 2_112, places=0)
        # Puis décote couple : 1 483 − 45,25 % × 2 112 = 527,3 → 1 585 €.
        self.assertEqual(impot_revenu(54_000, Foyer(couple=True, enfants=2)), 1_585)

    def test_celibataire_sans_decote(self):
        # 40 000 € : (29 579 − 11 600) × 11 % + (40 000 − 29 579) × 30 % = 5 104,0
        self.assertEqual(impot_revenu(40_000, Foyer()), 5_104)

    def test_decote(self):
        # 20 000 € : impôt brut 924 € < 1 982 € → décote 897 − 0,4525 × 924 = 478,9
        self.assertEqual(impot_revenu(20_000, Foyer()), 445)

    def test_plafonnement_quotient_familial(self):
        # Couple aisé avec 1 enfant : l'enfant ne peut pas faire gagner plus de 1 807 €.
        sans = impot_revenu(200_000, Foyer(couple=True))
        avec = impot_revenu(200_000, Foyer(couple=True, enfants=1))
        self.assertEqual(sans - avec, 1_807)

    def test_revenu_nul(self):
        self.assertEqual(impot_revenu(0, Foyer()), 0)


class TestLocation(unittest.TestCase):
    foyer = Foyer(autres_revenus=40_000)

    def test_longue_duree_micro(self):
        r = imposer("longue_duree", 18_000, 900, Bien(), self.foyer)
        self.assertEqual(r.regime, "Micro-BIC")
        self.assertEqual(r.revenu_imposable, 9_000)
        self.assertEqual(r.impot_revenu, 2_700)              # tranche à 30 %
        self.assertAlmostEqual(r.social, 9_000 * 0.186)

    def test_airbnb_au_dessus_de_15_000_passe_au_reel(self):
        r = imposer("tourisme_non_classe", 20_000, 5_000, Bien(charges_proprietaire=1_000),
                    self.foyer)
        self.assertEqual(r.regime, "Réel")
        self.assertEqual(r.revenu_imposable, 14_000)
        self.assertTrue(r.alertes)

    def test_reel_choisi_si_plus_favorable(self):
        bien = Bien(charges_proprietaire=2_000, valeur=400_000, mobilier=7_000)
        r = imposer("longue_duree", 18_000, 900, bien, self.foyer)
        self.assertEqual(r.regime, "Réel")                   # amortissement > abattement
        self.assertLess(r.total, imposer("longue_duree", 18_000, 900, Bien(), self.foyer).total)

    def test_cotisations_au_dessus_de_23_000(self):
        r = imposer("tourisme_non_classe", 30_000, 6_000, Bien(), self.foyer,
                    taux_cotisations=0.40)
        self.assertEqual(r.social_nature, "cotisations sociales")
        self.assertAlmostEqual(r.social, 24_000 * 0.40)


if __name__ == "__main__":
    unittest.main()
