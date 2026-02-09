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
        payload += b'trailing_junk'
        
        compressor = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)
        compressed = compressor.compress(payload) + compressor.flush()
        
        with open(path, 'wb') as f:
            f.write(header + compressed + b'END_MAGIC')

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

if __name__ == "__main__":
    unittest.main()
