import json
import unittest
from pathlib import Path

from labyrinth.plugins.breadcrumb_labyrinth.engine import Engine
from labyrinth.plugins.breadcrumb_labyrinth.loader import load_usable_types, validate_world


PLUGIN_DIR = Path("labyrinth/plugins/breadcrumb_labyrinth")


class BreadcrumbLabyrinthTests(unittest.TestCase):
    def test_happy_path(self):
        engine = Engine(PLUGIN_DIR)
        state = None

        output, state, _, _ = engine.handle(state, "Enter")
        self.assertIn("Room 1", output)

        output, state, _, _ = engine.handle(state, "Use")
        self.assertIn("button", output.lower())

        output, state, _, _ = engine.handle(state, "Get")
        self.assertIn("bronze key", output.lower())

        output, state, _, _ = engine.handle(state, "E")
        self.assertIn("Room 2", output)

        output, state, _, _ = engine.handle(state, "Use Bronze Key")
        self.assertIn("paper", output.lower())

        output, state, _, passed = engine.handle(state, "Submit 3F2504E0-4F89-11D3-9A0C-0305E82C3301")
        self.assertTrue(passed)
        self.assertIn("PASS", output)

    def test_button_reveals_once(self):
        engine = Engine(PLUGIN_DIR)
        state = None
        _, state, _, _ = engine.handle(state, "Enter")

        output, state, _, _ = engine.handle(state, "Use")
        self.assertIn("button", output.lower())
        output2, state, _, _ = engine.handle(state, "Use")
        self.assertIn("nothing else happens", output2.lower())

    def test_door_reveals_exit(self):
        engine = Engine(PLUGIN_DIR)
        state = None
        _, state, _, _ = engine.handle(state, "Enter")
        _, state, _, _ = engine.handle(state, "Use")
        _, state, _, _ = engine.handle(state, "Get")
        _, state, _, _ = engine.handle(state, "E")
        _, state, _, _ = engine.handle(state, "S")

        output, state, _, _ = engine.handle(state, "Use Bronze Key")
        self.assertIn("door", output.lower())

        output, state, _, _ = engine.handle(state, "E")
        self.assertIn("Room 4", output)

    def test_validation_errors(self):
        usable_types = load_usable_types(PLUGIN_DIR / "usable_types.json")

        base_world = json.loads((PLUGIN_DIR / "world.json").read_text(encoding="utf-8"))

        # start_room missing
        bad = json.loads(json.dumps(base_world))
        bad["start_room"] = "nope"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # bad exit
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room1"]["exits"]["N"] = "nope"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # unknown floor item
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room1"]["floor_item"] = "nope"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # unknown usable type
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room1"]["usable"]["type"] = "Lamp"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # duplicate usable ids
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room2"]["usable"]["id"] = bad["rooms"]["room1"]["usable"]["id"]
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # requires_item but not locked
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room2"]["usable"]["locked"] = False
        bad["rooms"]["room2"]["usable"]["requires_item"] = "key_bronze"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # door bad direction
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room3"]["usable"]["reveals_exit"]["direction"] = "Q"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)

        # door unknown room
        bad = json.loads(json.dumps(base_world))
        bad["rooms"]["room3"]["usable"]["reveals_exit"]["to_room"] = "nope"
        with self.assertRaises(ValueError):
            validate_world(bad, usable_types)


if __name__ == "__main__":
    unittest.main()
