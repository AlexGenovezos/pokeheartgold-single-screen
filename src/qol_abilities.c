#include "qol_abilities.h"

#include "constants/abilities.h"
#include "constants/species.h"
#include "qol_config.h"

BOOL Qol_IsSupportedAbility(u16 ability) {
    return ability <= NUM_ABILITIES
#if QOL_MODERN_BATTLE
        || ability == ABILITY_CURSED_BODY
#endif
        ;
}

u8 Qol_GetStoredAbility(u16 species, u8 form, u8 ability) {
#if QOL_MODERN_BATTLE
    // Gengar's original [Levitate, None] pair resolves to Levitate for both
    // PID parities. Preserve every explicitly stored nonstandard choice.
    if (species == SPECIES_GENGAR && form == 0 && ability == ABILITY_LEVITATE) {
        return ABILITY_CURSED_BODY;
    }
#endif
    return ability;
}

void Qol_ApplyModernMonAbilities(int species, BASE_STATS *personal) {
#if QOL_MODERN_BATTLE
    if (species == SPECIES_GENGAR) {
        personal->abilities[0] = ABILITY_CURSED_BODY;
        personal->abilities[1] = ABILITY_CURSED_BODY;
    }
#endif
}
