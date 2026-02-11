import os
import zlib
import unittest
import subprocess
import shutil
from naheulbeuk_patch import NaheulbeukSave

class TestNaheulbeukPatchers(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/bizon_test"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        self.save_path = os.path.join(self.test_dir, "test_save.sav")
        self.create_dummy_save(self.save_path)

    def create_dummy_save(self, path):
        header = b'UNITY_HEADER_DUMMY'
        # Create a payload with m_gold and perk fields
        # Entity 1: Gold 500, Perks 1,2,3
        # Entity 2: Gold 1000, Perks 0,0,0
        payload = b'some_junk'
        payload += b'm_gold' + (500).to_bytes(4, 'little')
        payload += b'm_activeSkillPoints' + (1).to_bytes(4, 'little')
        payload += b'm_passiveSkillPoints' + (2).to_bytes(4, 'little')
        payload += b'm_statsPoints' + (3).to_bytes(4, 'little')
        payload += b'between_entities'
        payload += b'm_gold' + (1000).to_bytes(4, 'little')
        payload += b'm_activeSkillPoints' + (0).to_bytes(4, 'little')
        payload += b'm_passiveSkillPoints' + (0).to_bytes(4, 'little')
        payload += b'm_statsPoints' + (0).to_bytes(4, 'little')
        payload += b'stats_block_start'
        payload += self.build_stats_slot(
            level=3,
            values={
                'agility': 10,
                'strength': 11,
                'constitution': 12,
                'courage': 13,
                'charisma': 14,
                'cleverness': 15,
            }
        )
        payload += b'between_stats_slots'
        payload += self.build_stats_slot(
            level=5,
            values={
                'agility': 20,
                'strength': 21,
                'constitution': 22,
                'courage': 23,
                'charisma': 24,
                'cleverness': 25,
            }
        )
        payload += b'trailing_junk'
        
        compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        compressed = compressor.compress(payload) + compressor.flush()
        
        with open(path, 'wb') as f:
            f.write(header + compressed + b'END_MAGIC')

    def build_stats_slot(self, level, values):
        payload = b'm_statsManager'
        payload += b'm_currentLevel' + int(level).to_bytes(4, 'little', signed=True)

        # This order mirrors discovered serialized order in real saves.
        ordered_fields = [
            ('agility', b'm_agility'),
            ('charisma', b'm_charisma'),
            ('cleverness', b'm_cleverness'),
            ('constitution', b'm_constitution'),
            ('courage', b'm_courage'),
            ('strength', b'm_strength'),
        ]

        for key, marker in ordered_fields:
            current = int(values[key])
            payload += marker
            payload += b'm_baseValueOverride' + current.to_bytes(4, 'little', signed=True)
            payload += b'm_value' + current.to_bytes(4, 'little', signed=True)

        return payload

    def extract_slots(self, data):
        def find_all(blob, marker):
            offsets = []
            start = 0
            while True:
                idx = blob.find(marker, start)
                if idx == -1:
                    break
                offsets.append(idx)
                start = idx + 1
            return offsets

        stat_markers = {
            'agility': b'm_agility',
            'charisma': b'm_charisma',
            'cleverness': b'm_cleverness',
            'constitution': b'm_constitution',
            'courage': b'm_courage',
            'strength': b'm_strength',
        }

        manager_offsets = find_all(data, b'm_statsManager')
        slots = []

        for i, sm in enumerate(manager_offsets):
            end = manager_offsets[i + 1] if i + 1 < len(manager_offsets) else len(data)
            block = data[sm:end]
            stats = {}
            complete = True

            for name, marker in stat_markers.items():
                rel_stat = block.find(marker)
                if rel_stat == -1:
                    complete = False
                    break

                abs_stat = sm + rel_stat
                base_marker = data.find(b'm_baseValueOverride', abs_stat, min(abs_stat + 220, len(data)))
                value_marker = data.find(b'm_value', base_marker + 1, min(abs_stat + 260, len(data)))
                if base_marker == -1 or value_marker == -1:
                    complete = False
                    break

                base_offset = base_marker + len(b'm_baseValueOverride')
                value_offset = value_marker + len(b'm_value')
                stats[name] = {
                    'base': int.from_bytes(data[base_offset:base_offset + 4], 'little', signed=True),
                    'value': int.from_bytes(data[value_offset:value_offset + 4], 'little', signed=True),
                }

            if complete:
                slots.append(stats)

        return slots

    def test_gold_patch_player_unique(self):
        # Patch 500 -> 9999
        cmd = ["python3", "patch_gold.py", self.save_path, "9999", "--current", "500"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Successfully saved", result.stdout)
        
        # Verify
        patched_save = NaheulbeukSave(self.save_path + ".patched")
        data = patched_save.load()
        self.assertIn(b'm_gold' + (9999).to_bytes(4, 'little'), data)
        self.assertIn(b'm_gold' + (1000).to_bytes(4, 'little'), data) # Second one unchanged

    def test_gold_patch_player_not_unique_fail(self):
        # Create save with two 500s
        header = b'UNITY'
        payload = b'm_gold' + (500).to_bytes(4, 'little') + b'm_gold' + (500).to_bytes(4, 'little')
        compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        compressed = compressor.compress(payload) + compressor.flush()
        with open(self.save_path, 'wb') as f:
            f.write(header + compressed)
            
        cmd = ["python3", "patch_gold.py", self.save_path, "9999", "--current", "500"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Multiple 'm_gold' fields found", result.stdout)

    def test_perks_patch_player(self):
        # Patch Entity 1: 1,2,3 -> 99
        cmd = ["python3", "patch_perks.py", self.save_path, "99", 
               "--current-active", "1", "--current-passive", "2", "--current-stats", "3"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        
        patched_save = NaheulbeukSave(self.save_path + ".perks.patched")
        data = patched_save.load()
        self.assertIn(b'm_activeSkillPoints' + (99).to_bytes(4, 'little'), data)
        self.assertIn(b'm_activeSkillPoints' + (0).to_bytes(4, 'little'), data) # Entity 2 unchanged

    def test_dry_run(self):
        cmd = ["python3", "patch_gold.py", self.save_path, "9999", "--current", "500", "--dry-run"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Dry-run complete", result.stdout)
        self.assertFalse(os.path.exists(self.save_path + ".patched"))

    def test_stats_list_slots(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--list-slots"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Discovered 2 complete stat slots", result.stdout)
        self.assertIn("Slot 1", result.stdout)
        self.assertIn("Slot 2", result.stdout)
        self.assertFalse(os.path.exists(self.save_path + ".stats.patched"))

    def test_stats_patch_slot_only(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--agility", "42",
            "--intelligence", "43",
            "--current-agility", "10",
            "--current-intelligence", "15",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        patched_save = NaheulbeukSave(self.save_path + ".stats.patched")
        data = patched_save.load()
        slots = self.extract_slots(data)
        self.assertEqual(len(slots), 2)

        self.assertEqual(slots[0]['agility']['base'], 10)
        self.assertEqual(slots[0]['agility']['value'], 42)
        self.assertEqual(slots[0]['cleverness']['base'], 15)
        self.assertEqual(slots[0]['cleverness']['value'], 43)

        self.assertEqual(slots[1]['agility']['base'], 20)
        self.assertEqual(slots[1]['agility']['value'], 20)
        self.assertEqual(slots[1]['cleverness']['base'], 25)
        self.assertEqual(slots[1]['cleverness']['value'], 25)

    def test_stats_patch_all(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--mode", "all", "--strength", "77"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        patched_save = NaheulbeukSave(self.save_path + ".stats.patched")
        data = patched_save.load()
        slots = self.extract_slots(data)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]['strength']['base'], 11)
        self.assertEqual(slots[0]['strength']['value'], 77)
        self.assertEqual(slots[1]['strength']['base'], 21)
        self.assertEqual(slots[1]['strength']['value'], 77)

    def test_stats_cleverness_alias(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--cleverness", "66",
            "--current-cleverness", "15",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        patched_save = NaheulbeukSave(self.save_path + ".stats.patched")
        data = patched_save.load()
        slots = self.extract_slots(data)
        self.assertEqual(slots[0]['cleverness']['base'], 15)
        self.assertEqual(slots[0]['cleverness']['value'], 66)

    def test_stats_slot_requires_current_values(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--slot", "1", "--agility", "40"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing required current stat flags", result.stdout)

    def test_stats_slot_requires_current_for_each_patched_stat(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--agility", "40",
            "--strength", "41",
            "--current-agility", "10",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--current-strength", result.stdout)

    def test_stats_slot_current_mismatch(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--agility", "40",
            "--current-agility", "999",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Current stat mismatch", result.stdout)
        self.assertFalse(os.path.exists(self.save_path + ".stats.patched"))

    def test_stats_current_int_alias_conflict(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--agility", "40",
            "--current-agility", "10",
            "--current-intelligence", "15",
            "--current-cleverness", "16",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict", result.stdout)

    def test_stats_int_alias_conflict(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--intelligence", "55",
            "--cleverness", "56",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflict", result.stdout)

    def test_stats_range_validation(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--slot", "1", "--agility", "1000"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Allowed range is 0..999", result.stdout)

    def test_stats_requires_any_stat_flag(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--slot", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("At least one stat flag is required", result.stdout)

    def test_stats_slot_out_of_range(self):
        cmd = ["python3", "patch_stats.py", self.save_path, "--slot", "99", "--agility", "10"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--slot out of range", result.stdout)

    def test_stats_dry_run(self):
        cmd = [
            "python3", "patch_stats.py", self.save_path,
            "--slot", "1",
            "--agility", "33",
            "--current-agility", "10",
            "--dry-run",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Dry-run complete", result.stdout)
        self.assertFalse(os.path.exists(self.save_path + ".stats.patched"))

if __name__ == "__main__":
    unittest.main()
