import csv
import os
import pickle
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import yaml
from autologic.app import load_event, main


ALGORITHM_NAME = "randomize"
SEED = 1337


@contextmanager
def chdir(path):
    """Temporarily change the working directory.

    Args:
        path: Destination directory to switch into for the block.
    """

    original_cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_cwd)


class TestIntegrationMain(unittest.TestCase):
    """Integration coverage for the randomize algorithm."""

    def test_main_generates_outputs_with_seed(self):
        """Runs the randomize algorithm and validates outputs for a fixed seed."""

        repo_root = Path(__file__).resolve().parents[1]
        config_path = repo_root / "tests" / "sample_event_config.yaml"
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

        config_data["name"] = "integration-event"
        config_data["axware_export_tsv"] = str(
            (repo_root / config_data["axware_export_tsv"]).resolve()
        )
        config_data["member_attributes_csv"] = str(
            (repo_root / config_data["member_attributes_csv"]).resolve()
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            with chdir(tmp_dir):
                event = load_event(
                    name=config_data["name"],
                    axware_export_tsv=config_data["axware_export_tsv"],
                    member_attributes_csv=config_data["member_attributes_csv"],
                    number_of_heats=config_data["number_of_heats"],
                    custom_assignments=config_data.get("custom_assignments", {}),
                    number_of_stations=config_data["number_of_stations"],
                    heat_size_parity=config_data["heat_size_parity"],
                    novice_size_parity=config_data["novice_size_parity"],
                    novice_denominator=config_data["novice_denominator"],
                    max_iterations=config_data["max_iterations"],
                    seed=SEED,
                )
                main(algorithm=ALGORITHM_NAME, event=event, interactive=False)

                tmp_path = Path(tmp_dir)
                csv_path = tmp_path / f"{event.name}.csv"
                pdf_path = tmp_path / f"{event.name}.pdf"
                pkl_path = tmp_path / f"{event.name}.pkl"

                for path in (csv_path, pdf_path, pkl_path):
                    self.assertTrue(path.exists())
                    self.assertGreater(path.stat().st_size, 0)

                with csv_path.open(newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader)
                    rows = list(reader)

                self.assertEqual(
                    header,
                    ["heat", "name", "class", "number", "assignment", "checked_in"],
                )
                self.assertEqual(len(rows), len(event.participants))

                matches = [row for row in rows if row[1] == "Thomas, Mia"]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0][4], "special")

                matches = [row for row in rows if row[1] == "Johnson, Noah"]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0][4], "instructor")

                matches = [row for row in rows if row[1] == "Taylor, Henry"]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0][4], "special")

                matches = [row for row in rows if row[1] == "Clark, Jackson"]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0][4], "instructor")

                with pdf_path.open("rb") as handle:
                    self.assertEqual(handle.read(4), b"%PDF")

                with pkl_path.open("rb") as handle:
                    loaded_event = pickle.load(handle)
                self.assertTrue(loaded_event.validate())
