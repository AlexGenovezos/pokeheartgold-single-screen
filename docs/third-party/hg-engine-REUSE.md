# hg-engine reference and reuse

Reference revision: `BluRosie/hg-engine@61b510cfb6cf7d77c3b083150fad3499f82fd326`.
Project: https://github.com/BluRosie/hg-engine

The modern type/species/move mapping and battle-rule ports consult this project.
Its full credits are retained in [hg-engine-CREDITS.md](hg-engine-CREDITS.md).
Retain those credits and these terms in derivatives that use adopted work.

The upstream README grants reuse subject to these conditions:

> You have my blessing to use code and assets from this repository as you please
> as long as there is *no money involved*, including optional donations through
> whichever platform to play your hack. The creations that stem from this
> repository must be freely accessible and not hidden at all behind any paywall,
> including those that prompt the player to pay optionally (Ko-Fi's style comes
> to mind here). The [Credits] should also be replicated in your hack's
> repository and/or the post to your hack--we all sit on the shoulders of giants here.

This source port does not bundle game ROMs, saves, proprietary SDK/compiler
files or generated native game code. The Fairy icon in `tools/qol/modern_rom.py`
is original source-generated artwork using the supplied game's existing palette.

Data import must use an explicit Gen IX configuration. The pinned hg-engine
configuration enables five Champions alterations by default; those are disabled
for this target. Its new move IDs are official move IDs plus three because it
retains the original HGSS placeholder members 468–470. Importers must record the
ID mapping and translate flags rather than silently copying incompatible bits.
