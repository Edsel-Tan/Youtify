#pragma once
#include "songmanager.h"

void download_song(const char*, const char*);
int load_songs(SongList*);
void save_songs(SongList*);