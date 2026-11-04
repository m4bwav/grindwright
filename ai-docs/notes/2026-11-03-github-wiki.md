# GitHub wiki

Pages: Home, Getting-Started, Commands, How-Work-Is-Ranked, Errors-and-Edge-Cases, Running-Unattended, Versions-and-Upgrading, FAQ, Development, plus sidebar and footer. Working copy: `grindwright.wiki`, a sibling of the clone.

Not on a registry, so examples run against a fresh clone of the repository: `2026-11-03-wiki-verify.py <ref>`, output saved beside it. Windows run only; Linux and macOS are covered by CI's tests, not by this script. Item ids change per run, so pages avoid showing them.

Not tested for the wiki: `grind_loop.py --go`, the plugin install lines, the eval command.

Update: rerun the script against the new tag, `wikiwright.py diffout` against the saved output, fix the pages named by the differences, then bump the footer and Versions-and-Upgrading.
