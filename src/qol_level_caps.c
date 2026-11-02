#include "qol_level_caps.h"

#include "constants/badge.h"
#include "constants/pokemon.h"
#include "constants/trainers.h"

typedef struct QolBadgeLevelCap {
    u8 badge;
    QolLevelCap cap;
} QolBadgeLevelCap;

// Badge order breaks equal-level ties; ace levels come from original teams.
static const QolBadgeLevelCap sJohtoLevelCaps[] = {
    { BADGE_ZEPHYR, { TRAINER_LEADER_FALKNER_FALKNER, 13 } },
    { BADGE_HIVE, { TRAINER_LEADER_BUGSY_BUGSY, 17 } },
    { BADGE_PLAIN, { TRAINER_LEADER_WHITNEY, 19 } },
    { BADGE_FOG, { TRAINER_LEADER_MORTY_MORTY, 25 } },
    { BADGE_STORM, { TRAINER_LEADER_CHUCK_CHUCK, 31 } },
    { BADGE_MINERAL, { TRAINER_LEADER_JASMINE_JASMINE, 35 } },
    { BADGE_GLACIER, { TRAINER_LEADER_PRYCE_PRYCE, 34 } },
    { BADGE_RISING, { TRAINER_LEADER_CLAIR_CLAIR, 41 } }
};

static const QolBadgeLevelCap sKantoLevelCaps[] = {
    { BADGE_BOULDER, { TRAINER_LEADER_BROCK_BROCK, 54 } },
    { BADGE_CASCADE, { TRAINER_LEADER_MISTY_MISTY, 54 } },
    { BADGE_THUNDER, { TRAINER_LEADER_LT_SURGE_LT__SURGE, 53 } },
    { BADGE_RAINBOW, { TRAINER_LEADER_ERIKA_ERIKA, 56 } },
    { BADGE_SOUL, { TRAINER_LEADER_JANINE_JANINE, 50 } },
    { BADGE_MARSH, { TRAINER_LEADER_SABRINA_SABRINA, 55 } },
    { BADGE_VOLCANO, { TRAINER_LEADER_BLAINE_BLAINE, 59 } },
    { BADGE_EARTH, { TRAINER_LEADER_BLUE_BLUE, 60 } }
};

static const QolLevelCap sLeagueLevelCaps[] = {
    { TRAINER_ELITE_FOUR_WILL_WILL, 42 },
    { TRAINER_ELITE_FOUR_KOGA_KOGA, 44 },
    { TRAINER_ELITE_FOUR_BRUNO_BRUNO, 46 },
    { TRAINER_ELITE_FOUR_KAREN_KAREN, 47 },
    { TRAINER_CHAMPION_LANCE, 50 }
};

QolLevelCap Qol_GetLevelCap(u16 badges, BOOL gameClear, u8 defeatedEliteFour) {
    const QolBadgeLevelCap *leaders = gameClear ? sKantoLevelCaps : sJohtoLevelCaps;
    QolLevelCap result = { TRAINER_NONE, MAX_LEVEL };
    int i;

    // Post-clear rematches can reset the League attempt flags. They must never
    // send Kanto progression back to the first League member's cap.
    for (i = 0; i < 8; i++) {
        if (!(badges & (1 << leaders[i].badge)) && leaders[i].cap.level < result.level) {
            result = leaders[i].cap;
        }
    }
    if (gameClear || result.trainerId != TRAINER_NONE) {
        return result;
    }

    for (i = 0; i < 4; i++) {
        if (!(defeatedEliteFour & (1 << i))) {
            return sLeagueLevelCaps[i];
        }
    }
    return sLeagueLevelCaps[4];
}

BOOL Qol_LevelCapConfigEnabled(u16 value) {
    // Original saves and unrecognised schema values remain Off.
    return value == QOL_LEVEL_CAP_CONFIG_ON;
}

u16 Qol_LevelCapConfigValue(BOOL enabled) {
    return enabled ? QOL_LEVEL_CAP_CONFIG_ON : QOL_LEVEL_CAP_CONFIG_OFF;
}

u32 Qol_LevelCapAllowedExp(BOOL enabled, u32 oldExp, u32 requestedExp, u32 capExp) {
    u32 remaining;
    if (!enabled) {
        return requestedExp;
    }
    if (oldExp >= capExp) {
        return 0;
    }
    // Subtract first: a large requested award must not wrap existing EXP.
    remaining = capExp - oldExp;
    return requestedExp < remaining ? requestedExp : remaining;
}
