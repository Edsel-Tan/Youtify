#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include "consts.h"
#include "filemanager.h"
#include "songmanager.h"

int main() {
    download_song("https://www.youtube.com/watch?v=DaJZjG7ByPU", "test");

    Song song = {};
    SongList songList;
    
    init_sl(&songList);
    push_back_sl(&songList, &song);
}