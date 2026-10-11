#include "campaign_audio.h"
#include "sound.h"

#define NO_SONG 255

static const UBYTE s_pSectorSongs[] = {
	SOUND_MUSIC_SECTOR1, SOUND_MUSIC_SECTOR2,
	SOUND_MUSIC_SECTOR3, SOUND_MUSIC_SECTOR4
};
static UBYTE s_ubMuted;
static UBYTE s_ubPlaying = NO_SONG;
static UBYTE s_ubLevel = NO_SONG;
static tPhase s_ePhase = TITLE;

void campaignAudioReset(void) {
	s_ubPlaying = NO_SONG;
	s_ubLevel = NO_SONG;
	s_ePhase = TITLE;
}

void campaignAudioUpdate(UBYTE level, tPhase phase, UBYTE muteToggle) {
	UBYTE song = SOUND_MUSIC_THEME;
	UBYTE newGame = phase == SECTOR_INTRO && level == 0 &&
		(s_ePhase != SECTOR_INTRO || s_ubLevel != 0);
	if(phase != TITLE && level < 4) {
		song = s_pSectorSongs[level];
	}
	s_ePhase = phase;
	s_ubLevel = level;
	if(muteToggle) {
		s_ubMuted = !s_ubMuted;
	}
	if(s_ubMuted) {
		if(s_ubPlaying != NO_SONG) {
			soundMusicStop();
			s_ubPlaying = NO_SONG;
		}
		return;
	}
	if(song != s_ubPlaying || newGame) {
		soundMusicStart(song);
		s_ubPlaying = song;
	}
}
