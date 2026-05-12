import unittest

from scripts.custom_agents import (
    build_agent_record,
    build_test_preview,
    compile_prompt,
    list_templates,
)


class CustomAgentCompilerTests(unittest.TestCase):
    def _valid_payload(self, template_key="documentary_10_section"):
        return {
            "templateKey": template_key,
            "name": "Crimen corporativo",
            "description": "Documentales sobre fraudes, poder y consecuencias humanas.",
            "category": "business",
            "brief": {
                "niche": "fraudes corporativos, crisis empresariales y decisiones que destruyen companias",
                "audience": "adultos curiosos que aman documentales de negocios con tension narrativa",
                "promise": "entender como una decision aparentemente pequena puede revelar una cultura entera",
                "tone": "cinematografico, sobrio, investigativo y humano",
                "mustInclude": ["fechas", "personajes", "consecuencias humanas"],
                "mustAvoid": ["acusaciones sin fuente", "tono sensacionalista vacio"],
                "visualIdentity": "oficinas oscuras, documentos, juntas tensas, luz fria y detalles premium",
                "safetyNotes": "no acusar sin fuente y marcar revision humana cuando haya riesgo legal",
            },
            "exampleTopics": ["La caida de Enron"],
        }

    def test_templates_are_available(self):
        keys = {item["templateKey"] for item in list_templates()}
        self.assertIn("documentary_10_section", keys)
        self.assertIn("immersive_meditation", keys)
        self.assertIn("tiktok_podcast", keys)

    def test_documentary_compiler_keeps_ten_section_architecture(self):
        compiled = compile_prompt(self._valid_payload())
        self.assertEqual(compiled["validation"]["status"], "passed")
        prompt = compiled["compiledPrompt"]
        self.assertIn("AI AGENT: Crimen corporativo", prompt)
        self.assertIn("Use exactly 10 organic sections", prompt)
        self.assertIn("1. Initial hook", prompt)
        self.assertIn("10. Closing + CTA", prompt)

    def test_wellness_blocks_medical_guarantees(self):
        payload = self._valid_payload("long_meditation")
        payload["brief"]["promise"] = "curar depresion y eliminar ansiedad garantizado"
        payload["brief"]["safetyNotes"] = "wellness seguro sin promesas medicas"
        compiled = compile_prompt(payload)
        self.assertEqual(compiled["validation"]["status"], "failed")
        self.assertTrue(compiled["validation"]["issues"])

    def test_test_preview_requires_saved_record_shape(self):
        record = build_agent_record(self._valid_payload(), owner_uid="admin")
        preview = build_test_preview(record, "La caida de Enron")
        self.assertEqual(preview["status"], "passed")
        self.assertGreaterEqual(preview["scores"]["formatCompatibility"], 80)
        self.assertIn("La caida de Enron", preview["scriptPreview"])


if __name__ == "__main__":
    unittest.main()
