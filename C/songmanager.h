typedef struct {
    char title[256];
    char youtube_link[512];
    float rating;
    int rating_count;
} Song;

typedef struct {
    Song *songs;
    int count;
} SongList;

void init_sl(SongList*);
void push_back_sl(SongList*, Song*);
void delete_sl(SongList*);