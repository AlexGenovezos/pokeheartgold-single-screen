#include "qol_level_cap_save.h"

#include <stddef.h>

#include "constants/flags.h"
#include "constants/pokemon.h"
#include "constants/trainers.h"
#include "constants/vars.h"

#include "player_data.h"
#include "pokemon.h"
#include "qol_config.h"
#include "save_vars_flags.h"
#include "sys_flags.h"

// Keep the audited allocation and original save-block layout invariant, even
// in feature-disabled builds. The original SDK compiler does not require C11.
#define CAP_ASSERT(name, condition) typedef char name[(condition) ? 1 : -1]
CAP_ASSERT(CapFlagIsBoolean, QOL_LEVEL_CAPS == 0 || QOL_LEVEL_CAPS == 1);
CAP_ASSERT(CapVarBaseUnchanged, VAR_BASE == 0x4000);
CAP_ASSERT(CapVarCountUnchanged, NUM_VARS == 0x170);
CAP_ASSERT(CapPhaseSlotReserved, VAR_QOL_DAYCARE_BREEDING_PHASE == 0x416E);
CAP_ASSERT(CapConfigSlotReserved, VAR_QOL_LEVEL_CAP_CONFIG == 0x416F);
CAP_ASSERT(CapSlotsDistinct, VAR_QOL_DAYCARE_BREEDING_PHASE != VAR_QOL_LEVEL_CAP_CONFIG);
CAP_ASSERT(CapPhaseSlotPersistent, VAR_QOL_DAYCARE_BREEDING_PHASE >= VAR_BASE + NUM_TEMP_VARS && VAR_QOL_DAYCARE_BREEDING_PHASE <= VARS_END);
CAP_ASSERT(CapConfigSlotPersistent, VAR_QOL_LEVEL_CAP_CONFIG >= VAR_BASE + NUM_TEMP_VARS && VAR_QOL_LEVEL_CAP_CONFIG <= VARS_END);
CAP_ASSERT(CapVarsSizeUnchanged, sizeof(((SaveVarsFlags *)0)->vars) == 0x2E0);
CAP_ASSERT(CapFlagsOffsetUnchanged, offsetof(SaveVarsFlags, flags) == 0x2E0);
CAP_ASSERT(CapSaveBlockSizeUnchanged, sizeof(SaveVarsFlags) == 0x44C);
#undef CAP_ASSERT

QolLevelCap Qol_LevelCapForSave(SaveData *saveData) {
#if QOL_LEVEL_CAPS
    PlayerProfile *profile = Save_PlayerData_GetProfile(saveData);
    SaveVarsFlags *varsFlags = Save_VarsFlags_Get(saveData);
    u16 badges = 0;
    u8 defeated = 0;
    int badge;

    for (badge = 0; badge < 16; badge++) {
        if (PlayerProfile_TestBadgeFlag(profile, badge)) {
            badges |= 1 << badge;
        }
    }
    if (Save_VarsFlags_CheckFlagInArray(varsFlags, FLAG_DEFEATED_WILL)) {
        defeated |= QOL_LEVEL_CAP_DEFEATED_WILL;
    }
    if (Save_VarsFlags_CheckFlagInArray(varsFlags, FLAG_DEFEATED_KOGA)) {
        defeated |= QOL_LEVEL_CAP_DEFEATED_KOGA;
    }
    if (Save_VarsFlags_CheckFlagInArray(varsFlags, FLAG_DEFEATED_BRUNO)) {
        defeated |= QOL_LEVEL_CAP_DEFEATED_BRUNO;
    }
    if (Save_VarsFlags_CheckFlagInArray(varsFlags, FLAG_DEFEATED_KAREN)) {
        defeated |= QOL_LEVEL_CAP_DEFEATED_KAREN;
    }
    return Qol_GetLevelCap(badges, CheckGameClearFlag(varsFlags), defeated);
#else
    QolLevelCap cap = { TRAINER_NONE, MAX_LEVEL };
    return cap;
#endif
}

BOOL Qol_LevelCapEnabledForSave(SaveData *saveData) {
#if QOL_LEVEL_CAPS
    u16 *config = Save_VarsFlags_GetVarAddr(Save_VarsFlags_Get(saveData), VAR_QOL_LEVEL_CAP_CONFIG);
    return Qol_LevelCapConfigEnabled(*config);
#else
    return FALSE;
#endif
}

void Qol_LevelCapSetEnabledForSave(SaveData *saveData, BOOL enabled) {
#if QOL_LEVEL_CAPS
    u16 *config = Save_VarsFlags_GetVarAddr(Save_VarsFlags_Get(saveData), VAR_QOL_LEVEL_CAP_CONFIG);
    *config = Qol_LevelCapConfigValue(enabled);
#endif
}

u32 Qol_LevelCapLimitPlayerExp(SaveData *saveData, u16 species, u32 oldExp, u32 requestedExp) {
#if QOL_LEVEL_CAPS
    QolLevelCap cap;
    u32 capExp;
    if (!Qol_LevelCapEnabledForSave(saveData)) {
        return requestedExp;
    }
    cap = Qol_LevelCapForSave(saveData);
    if (cap.trainerId == TRAINER_NONE || cap.level == MAX_LEVEL) {
        return requestedExp;
    }
    capExp = GetMonExpBySpeciesAndLevel(species, cap.level);
    return Qol_LevelCapAllowedExp(TRUE, oldExp, requestedExp, capExp);
#else
    return requestedExp;
#endif
}

BOOL Qol_LevelCapCanUseRareCandy(SaveData *saveData, Pokemon *mon) {
#if QOL_LEVEL_CAPS
    u32 requestedExp;
    if (GetMonData(mon, MON_DATA_LEVEL, NULL) >= MAX_LEVEL) {
        return FALSE;
    }
    requestedExp = CalcMonExpToNextLevel(mon);
    return requestedExp != 0 && Qol_LevelCapLimitPlayerExp(saveData,
        GetMonData(mon, MON_DATA_SPECIES, NULL),
        GetMonData(mon, MON_DATA_EXPERIENCE, NULL), requestedExp) == requestedExp;
#else
    return TRUE;
#endif
}

u8 Qol_LevelCapAdvanceDaycarePhase(SaveData *saveData, DaycareMon *second) {
    if (!GetBoxMonData(DaycareMon_GetBoxMon(second), MON_DATA_SPECIES_EXISTS, NULL)) {
        Qol_LevelCapResetDaycarePhase(saveData);
        return 0;
    }
#if QOL_LEVEL_CAPS
    {
        u16 *stored = Save_VarsFlags_GetVarAddr(Save_VarsFlags_Get(saveData), VAR_QOL_DAYCARE_BREEDING_PHASE);
        u8 phase;
        if ((*stored & 0xFF00) == 0xD100) {
            phase = (u8)(*stored + 1);
        } else if (Qol_LevelCapEnabledForSave(saveData)) {
            // Read the old counter before this walk changes accepted growth.
            phase = (u8)(DaycareMon_GetSteps(second) + 1);
        } else {
            return (u8)(DaycareMon_GetSteps(second) + 1);
        }
        *stored = 0xD100 | phase;
        return phase;
    }
#else
    return (u8)(DaycareMon_GetSteps(second) + 1);
#endif
}

void Qol_LevelCapResetDaycarePhase(SaveData *saveData) {
#if QOL_LEVEL_CAPS
    u16 *stored = Save_VarsFlags_GetVarAddr(Save_VarsFlags_Get(saveData), VAR_QOL_DAYCARE_BREEDING_PHASE);
    if ((*stored & 0xFF00) == 0xD100 || Qol_LevelCapEnabledForSave(saveData)) {
        *stored = 0xD100;
    }
#endif
}
