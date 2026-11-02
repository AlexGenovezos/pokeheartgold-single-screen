#include "qol_abilities.h"

#include "constants/abilities.h"
#include "constants/species.h"
#include "qol_config.h"

BOOL Qol_IsSupportedAbility(u16 ability) {
    return ability <= NUM_ABILITIES
#if QOL_MODERN_BATTLE
        || ability == ABILITY_CURSED_BODY || ability == ABILITY_COMPETITIVE
        || ability == ABILITY_WIND_RIDER || ability == ABILITY_SHARPNESS
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
    // Gallade originally stores Steadfast in both standard slots. Recover only
    // that original byte for odd PIDs; explicit custom choices remain intact.
    if (species == SPECIES_GALLADE && form == 0 && ability == ABILITY_STEADFAST && (personality & 1)) {
        return ABILITY_SHARPNESS;
    }
    // Only Shiftry's original second slot (Early Bird) on an odd PID is
    // adapted. Even-PID custom bytes and every alternate form remain explicit.
    if (species == SPECIES_SHIFTRY && form == 0 && ability == ABILITY_EARLY_BIRD && (personality & 1)) {
        return ABILITY_WIND_RIDER;
    }
    if (form == 0 && (personality & 1)) {
        if (species == SPECIES_WINGULL && ability == ABILITY_KEEN_EYE) {
            return ABILITY_HYDRATION;
        } else if (species == SPECIES_PELIPPER && ability == ABILITY_KEEN_EYE) {
            return ABILITY_DRIZZLE;
        } else if (species == SPECIES_TORKOAL && ability == ABILITY_WHITE_SMOKE) {
            return ABILITY_DROUGHT;
        } else if (species == SPECIES_FEEBAS && ability == ABILITY_SWIFT_SWIM) {
            return ABILITY_OBLIVIOUS;
        }
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
    } else if (species == SPECIES_SHIFTRY) {
        personal->abilities[1] = ABILITY_WIND_RIDER;
    } else if (species == SPECIES_GALLADE) {
        personal->abilities[1] = ABILITY_SHARPNESS;
    } else if (species == SPECIES_WINGULL) {
        personal->abilities[1] = ABILITY_HYDRATION;
    } else if (species == SPECIES_PELIPPER) {
        personal->abilities[1] = ABILITY_DRIZZLE;
    } else if (species == SPECIES_TORKOAL) {
        personal->abilities[1] = ABILITY_DROUGHT;
    } else if (species == SPECIES_FEEBAS) {
        personal->abilities[1] = ABILITY_OBLIVIOUS;
    }
#endif
}
