import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import md_links  # noqa: E402
import md_tables  # noqa: E402
import pr_scope  # noqa: E402
import skill_budget  # noqa: E402

GOOD = "| a | b |\n|---|:-:|\n| 1 | 2 |\n"


class TableTests(unittest.TestCase):
    def test_good_table(self):
        self.assertEqual(md_tables.check_text(GOOD), [])

    def test_double_pipe_row(self):
        self.assertTrue(md_tables.check_text("| a | b |\n|---|---|\n|| 1 | 2 |\n"))

    def test_column_mismatch(self):
        self.assertTrue(md_tables.check_text("| a | b | c |\n|---|---|\n| 1 | 2 | 3 |\n"))

    def test_empty_delimiter_cell(self):
        self.assertTrue(md_tables.check_text("| a | b |\n|---| |\n| 1 | 2 |\n"))

    def test_fenced_ignored(self):
        self.assertEqual(md_tables.check_text("```\n|| x\n```\n"), [])


class LinkTests(unittest.TestCase):
    def setUp(self):
        md_links._anchor_cache.clear()
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def write(self, name, text):
        p = os.path.join(self.d.name, name)
        open(p, "w").write(text)
        return p

    def test_slug(self):
        self.assertEqual(md_links.slugify("Hello, World! `x` (v2)"), "hello-world-x-v2")

    def test_ok_and_duplicate_heading(self):
        p = self.write("a.md", "# A\n## Same\n## Same\n[x](#a) [y](#same-1) [z](b.md)\n")
        self.write("b.md", "x")
        self.assertEqual(md_links.check_text(open(p).read(), p), [])

    def test_broken(self):
        p = self.write("a.md", "# A\n[x](#nope) [y](missing.md) [z](https://e.com/x) `[c](zzz.md)`\n")
        self.assertEqual(len(md_links.check_text(open(p).read(), p)), 2)

    def test_cross_file_anchor(self):
        self.write("b.md", "# Bee\n")
        p = self.write("a.md", "[ok](b.md#bee) [bad](b.md#ant)\n")
        self.assertEqual(len(md_links.check_text(open(p).read(), p)), 1)


class BudgetTests(unittest.TestCase):
    def test_over_and_under(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                open("S.md", "w").write("one two three")
                cfg = os.path.join(d, "c.json")
                json.dump({"file": "S.md", "max_words": 3}, open(cfg, "w"))
                self.assertEqual(skill_budget.check(cfg), [])
                json.dump({"file": "S.md", "max_words": 2}, open(cfg, "w"))
                self.assertEqual(len(skill_budget.check(cfg)), 1)
            finally:
                os.chdir(cwd)


class ScopeTests(unittest.TestCase):
    def test_type(self):
        self.assertEqual(pr_scope.commit_type("docs(readme): x"), "docs")
        self.assertEqual(pr_scope.commit_type("feat!: x"), "feat")
        self.assertIsNone(pr_scope.commit_type("Update stuff"))

    def test_docs_pr_with_code_fails(self):
        self.assertTrue(pr_scope.scope_problems("docs: add sponsor", ["README.md", "forge/x.py"]))

    def test_docs_pr_clean(self):
        self.assertEqual(pr_scope.scope_problems("docs(x): y", ["README.md", "docs/a/b.md", "assets/i.png"]), [])

    def test_non_docs_title_unrestricted(self):
        self.assertEqual(pr_scope.scope_problems("feat: y", ["forge/x.py"]), [])

    def test_stacked_overlap(self):
        r = pr_scope.stacked_overlap(["a", "b"], [{"number": 5, "commits": ["b", "z"]}, {"number": 6, "commits": ["q"]}])
        self.assertEqual(r, {5: ["b"]})


if __name__ == "__main__":
    unittest.main()
