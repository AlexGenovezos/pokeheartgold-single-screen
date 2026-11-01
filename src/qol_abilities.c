#include "qol_abilities.h"

#include "constants/abilities.h"
#include "constants/species.h"
#include "qol_config.h"

BOOL Qol_IsSupportedAbility(u16 ability) {
    return ability <= NUM_ABILITIES
#if QOL_MODERN_BATTLE
        || ability == ABILITY_CURSED_BODY || ability == ABILITY_COMPETITIVE
#endif
        ;
}

u8 Qol_GetStoredAbility(u16 species, u8 form, u8 ability, u32 personality) {
#if QOL_MODERN_BATTLE
    // Gengar's original [Levitate, None] pair resolves to Levitate for both
    // PID parities. Preserve every explicitly stored nonstandard choice.
    if (species == SPECIES_GENGAR && form == 0 && ability == ABILITY_LEVITATE) {
        return ABILITY_CURSED_BODY;
    }
    // These original [first, None] pairs selected first for either PID parity.
    // Only recover that original standard choice; preserve explicit other bytes.
    if (form == 0 && (personality & 1)
        && (((species == SPECIES_JIGGLYPUFF || species == SPECIES_WIGGLYTUFF || species == SPECIES_IGGLYBUFF)
                && ability == ABILITY_CUTE_CHARM)
            || (species == SPECIES_MILOTIC && ability == ABILITY_MARVEL_SCALE))) {
        return ABILITY_COMPETITIVE;
    }
#endif
    return ability;
}

void Qol_ApplyModernMonAbilities(int species, BASE_STATS *personal) {
#if QOL_MODERN_BATTLE
    if (species == SPECIES_GENGAR) {
        personal->abilities[0] = ABILITY_CURSED_BODY;
        personal->abilities[1] = ABILITY_CURSED_BODY;
    } else if (species == SPECIES_JIGGLYPUFF || species == SPECIES_WIGGLYTUFF || species == SPECIES_IGGLYBUFF
        || species == SPECIES_MILOTIC) {
        personal->abilities[1] = ABILITY_COMPETITIVE;
    }
#endif
}
