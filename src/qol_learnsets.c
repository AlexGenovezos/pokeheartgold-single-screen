#include "qol_learnsets.h"

#include "qol_config.h"
#include "qol_moves.h"

#if QOL_MODERN_MOVES
static const struct {
    u16 species;
    u16 level;
    u16 move;
} sModernLevelUpAdditions[] = {
#define QOL_LEVEL_UP_MOVE(species, level, move) { species, level, move },
#include "data/qol_learnsets.inc"
#undef QOL_LEVEL_UP_MOVE
};
#endif

int Qol_LoadLevelUpLearnset(int species, int form, QolLevelUpMove *dest) {
    u16 legacy[MAX_LEARNED_MOVES];
    int count = 0;

    // The largest native NARC member is 44 bytes, including its sentinel and
    // alignment padding. Never read that member into the wider record array.
    LoadLevelUpLearnset_HandleAlternateForm(species, form, legacy);
    for (int i = 0; i < MAX_LEARNED_MOVES && legacy[i] != LEVEL_UP_LEARNSET_END; i++) {
        dest[count].move = LEVEL_UP_LEARNSET_MOVE(legacy[i]);
        dest[count].level = LEVEL_UP_LEARNSET_LVL(legacy[i]);
        count++;
    }
#if QOL_MODERN_MOVES
    // The pinned profile describes base forms only. Every alternate form and
    // native form-only species ID deliberately keeps its original NARC table.
    if (form == 0 && species >= SPECIES_BULBASAUR && species <= SPECIES_ARCEUS) {
        for (int i = 0; i < (int)NELEMS(sModernLevelUpAdditions); i++) {
            int position;
            BOOL duplicate = FALSE;
            if (sModernLevelUpAdditions[i].species != species
                || !Qol_IsSupportedMove(sModernLevelUpAdditions[i].move)) {
                continue;
            }
            for (int j = 0; j < count; j++) {
                if (dest[j].move == sModernLevelUpAdditions[i].move
                    && dest[j].level == sModernLevelUpAdditions[i].level) {
                    duplicate = TRUE;
                    break;
                }
            }
            if (duplicate || count >= QOL_LEVEL_UP_LEARNSET_CAPACITY - 1) {
                continue;
            }
            // Stable insertion keeps native moves at the same level in order.
            position = count;
            while (position > 0 && dest[position - 1].level > sModernLevelUpAdditions[i].level) {
                dest[position] = dest[position - 1];
                position--;
            }
            dest[position].move = sModernLevelUpAdditions[i].move;
            dest[position].level = sModernLevelUpAdditions[i].level;
            count++;
        }
    }
#endif
    dest[count].move = LEVEL_UP_LEARNSET_END;
    dest[count].level = 0;
    return count;
}

u32 Qol_MonTryLearnMove(Pokemon *mon, int *last_i, u16 *newMove, BOOL afterEvolution) {
    QolLevelUpMove *learnset = Heap_Alloc(HEAP_ID_DEFAULT, QOL_LEVEL_UP_LEARNSET_CAPACITY * sizeof(QolLevelUpMove));
    int species = GetMonData(mon, MON_DATA_SPECIES, NULL);
    int form = GetMonData(mon, MON_DATA_FORM, NULL);
    int level = GetMonData(mon, MON_DATA_LEVEL, NULL);
    int count = Qol_LoadLevelUpLearnset(species, form, learnset);
    u32 ret = 0;

    if (*last_i >= 0 && *last_i < count) {
        while (*last_i < count) {
            int i = (*last_i)++;
            if (learnset[i].level == level || (afterEvolution && learnset[i].level == 0)) {
                *newMove = learnset[i].move;
                ret = TryAppendMonMove(mon, *newMove);
                break;
            }
        }
    }
    Heap_Free(learnset);
    return ret;
}

u32 Qol_MonTryLearnMoveAfterEvolution(Pokemon *mon, int *last_i, u16 *newMove) {
#if QOL_MODERN_MOVES
    return Qol_MonTryLearnMove(mon, last_i, newMove, TRUE);
#else
    return MonTryLearnMoveOnLevelUp(mon, last_i, newMove);
#endif
}
