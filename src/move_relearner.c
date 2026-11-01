#include "move_relearner.h"

#include "global.h"

#include "pokemon.h"
#include "qol_learnsets.h"

MoveRelearnerArgs *MoveRelearner_New(enum HeapID heapID) {
    MoveRelearnerArgs *ret = Heap_Alloc(heapID, sizeof(MoveRelearnerArgs));
    memset(ret, 0, sizeof(MoveRelearnerArgs));
    return ret;
}

void MoveRelearner_Delete(MoveRelearnerArgs *moveRelearner) {
    Heap_Free(moveRelearner);
}

u16 *MoveRelearner_GetEligibleLevelUpMoves(Pokemon *mon, enum HeapID heapID) {
    u16 species = GetMonData(mon, MON_DATA_SPECIES, NULL);
    u8 form = GetMonData(mon, MON_DATA_FORM, NULL);
    u8 level = GetMonData(mon, MON_DATA_LEVEL, NULL);
    u16 moves[MAX_MON_MOVES];

    for (u8 i = 0; i < MAX_MON_MOVES; i++) {
        moves[i] = GetMonData(mon, MON_DATA_MOVE1 + i, NULL);
    }

    QolLevelUpMove *tableFromFile = Heap_Alloc(heapID, QOL_LEVEL_UP_LEARNSET_CAPACITY * sizeof(QolLevelUpMove));
    u16 *returnTable = Heap_Alloc(heapID, QOL_LEVEL_UP_LEARNSET_CAPACITY * sizeof(u16));
    int count = Qol_LoadLevelUpLearnset(species, form, tableFromFile);
    int k = 0;

    for (int i = 0; i < count; i++) {
        int j;
        u16 move = tableFromFile[i].move;
        if (tableFromFile[i].level > level) {
            continue;
        }
        for (j = 0; j < MAX_MON_MOVES; j++) {
            if (move == moves[j]) {
                break;
            }
        }
        if (j == MAX_MON_MOVES) {
            for (j = 0; j < k; j++) {
                if (returnTable[j] == move) {
                    break;
                }
            }
            if (j == k) {
                returnTable[k++] = move;
            }
        }
    }
    returnTable[k] = LEVEL_UP_LEARNSET_END;
    Heap_Free(tableFromFile);
    return returnTable;
}

BOOL MoveRelearner_IsValidMove(const u16 *ptr) {
    return *ptr != LEVEL_UP_LEARNSET_END;
}
