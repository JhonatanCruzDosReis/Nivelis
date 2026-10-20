import React, { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  StatusBar, Dimensions, ScrollView, ActivityIndicator,
  BackHandler,
} from 'react-native';
import { usePip, VideoSource } from '../../../../context/PipContext';
import { WebView } from 'react-native-webview';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useTheme } from '../../../TemasAcoes/Temas';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';

const { width, height: screenH } = Dimensions.get('window');
const NORMAL_H = Math.round(width * 9 / 16);
const CINEMA_H = Math.round(screenH * 0.62);
const ACCENT   = '#7D53DD';

function fmtTime(sec: number): string {
  if (!isFinite(sec) || sec < 0) return '0:00';
  const s = Math.floor(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

// ─── YouTube IFrame API (controls=0) ─────────────────────────────────────────
function buildYouTubeHTML(videoId: string): string {
  return `<!DOCTYPE html><html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
  <style>*{margin:0;padding:0;background:#000}html,body{width:100%;height:100%;overflow:hidden}#player{width:100%;height:100%}</style>
</head>
<body>
<div id="player"></div>
<script src="https://www.youtube.com/iframe_api"></script>
<script>
var player,timer;
function onYouTubeIframeAPIReady(){
  player=new YT.Player('player',{
    videoId:'${videoId}',
    playerVars:{autoplay:1,controls:0,rel:0,modestbranding:1,playsinline:1},
    events:{
      onReady:function(){timer=setInterval(sendState,500)},
      onStateChange:sendState
    }
  });
}
function sendState(){
  if(!player||!player.getCurrentTime)return;
  window.ReactNativeWebView.postMessage(JSON.stringify({
    current:player.getCurrentTime(),
    duration:player.getDuration(),
    playing:player.getPlayerState()===1
  }));
}
window.rnPlay       =function(){if(player)player.playVideo();};
window.rnPause      =function(){if(player)player.pauseVideo();};
window.rnSeek       =function(s){if(player)player.seekTo(Math.max(0,player.getCurrentTime()+s),true);};
window.rnSeekTo     =function(t){if(player)player.seekTo(t,true);};
window.rnFullscreen =function(){
  var el=document.getElementById('player')||document.documentElement;
  if(el.requestFullscreen)el.requestFullscreen();
  else if(el.webkitRequestFullscreen)el.webkitRequestFullscreen();
};
window.rnPiP=function(){
  var iframes=document.querySelectorAll('iframe');
  for(var i=0;i<iframes.length;i++){
    try{
      var v=iframes[i].contentDocument&&iframes[i].contentDocument.querySelector('video');
      if(v&&document.pictureInPictureEnabled){v.requestPictureInPicture();return;}
    }catch(e){}
  }
};
</script>
</body></html>`;
}

// ─── Drive: HTML próprio com <video> direto (sem iframe cross-origin) ────────
// O /preview do Drive roda o player em iframe cross-origin → injectJavaScript
// nunca chega no <video>. Solução: montar nosso próprio HTML com a URL de
// download direto do Drive como source — o <video> fica no nosso documento.
function buildDriveHTML(videoId: string): string {
  const src = `https://drive.google.com/uc?id=${videoId}&export=download`;
  return `<!DOCTYPE html><html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
  <style>
    *{margin:0;padding:0;box-sizing:border-box;background:#000}
    html,body{width:100%;height:100%;overflow:hidden}
    #v{width:100%;height:100%;object-fit:contain;background:#000;display:block}
  </style>
</head>
<body>
<video id="v" autoplay playsinline preload="auto">
  <source src="${src}" type="video/mp4">
</video>
<script>
var v=document.getElementById('v'),_t=0;

/* sendNow: sempre envia — usado em play/pause/seeked */
function sendNow(){
  window.ReactNativeWebView.postMessage(JSON.stringify({
    current:v.currentTime,
    duration:isFinite(v.duration)?v.duration:0,
    playing:!v.paused&&!v.ended
  }));
}
/* sendThrottled: usado só no timeupdate (evita flood) */
function sendThrottled(){
  var now=Date.now();if(now-_t<300)return;_t=now;sendNow();
}
v.addEventListener('timeupdate', sendThrottled);
v.addEventListener('play',   sendNow);
v.addEventListener('pause',  sendNow);
v.addEventListener('seeked', sendNow);
v.addEventListener('error',function(){
  window.ReactNativeWebView.postMessage(JSON.stringify({videoError:true}));
});
window.rnPlay   =function(){ var p=v.play(); if(p)p.catch(function(){}); sendNow(); };
window.rnPause  =function(){ v.pause(); sendNow(); };
window.rnSeek   =function(s){ v.currentTime=Math.max(0,v.currentTime+s); sendNow(); };
window.rnSeekTo =function(t){ v.currentTime=t; sendNow(); };
</script>
</body></html>`;
}

export default function AulaPlayer() {
  const navigation      = useNavigation<any>();
  const route           = useRoute<any>();
  const { isDarkMode }  = useTheme();
  const { modal }       = useNivelisModal();
  const webRef          = useRef<any>(null);

  const {
    titulo      = 'Aula',
    duracao     = '',
    materiaNome = '',
    videoId     = null,
    videoTipo   = 'youtube',
  } = route.params ?? {};

  const { startPip, stopPip, isPip } = usePip();

  const [loading,     setLoading]     = useState(true);
  const [erro,        setErro]        = useState(false);
  const [playing,     setPlaying]     = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration,    setDuration]    = useState(0);
  const [progWidth,   setProgWidth]   = useState(1);
  const [cinema,      setCinema]      = useState(false);
  const [fullscreen,  setFullscreen]  = useState(false);

  const theme = {
    bg:     isDarkMode ? '#000000' : '#F5F5F7',
    text:   isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:    isDarkMode ? '#888888' : '#666666',
    border: isDarkMode ? '#222222' : '#E5E5E5',
  };

  const cmd = useCallback((js: string) => {
    webRef.current?.injectJavaScript(js + ';true;');
  }, []);

  const togglePlay   = useCallback(() => { playing ? cmd('window.rnPause()') : cmd('window.rnPlay()'); }, [playing, cmd]);
  const seekRelative = useCallback((s: number) => { cmd(`window.rnSeek(${s})`); }, [cmd]);
  const seekTo       = useCallback((ratio: number) => {
    if (duration > 0) cmd(`window.rnSeekTo(${Math.max(0, Math.min(1, ratio)) * duration})`);
  }, [duration, cmd]);

  // Fullscreen: estado RN — requestFullscreen() via JS é bloqueado pelo WebView
  const handleFullscreen = useCallback(() => {
    setFullscreen(f => {
      const next = !f;
      StatusBar.setHidden(next, 'fade');
      return next;
    });
  }, []);

  const toggleCinema = useCallback(() => setCinema(c => !c), []);

  // Sair do fullscreen com botão voltar (Android)
  useEffect(() => {
    if (!fullscreen) return;
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      setFullscreen(false);
      StatusBar.setHidden(false, 'fade');
      return true;
    });
    return () => sub.remove();
  }, [fullscreen]);

  const onMessage = useCallback((e: any) => {
    try {
      const d = JSON.parse(e.nativeEvent.data);
      if (d.videoError) { setLoading(false); setErro(true); return; }
      if (typeof d.current  === 'number') setCurrentTime(d.current);
      if (typeof d.duration === 'number' && d.duration > 0) setDuration(d.duration);
      if (typeof d.playing  === 'boolean') setPlaying(d.playing);
    } catch {}
  }, []);

  const isDrive = videoTipo === 'drive';

  // webSource calculado antes do early return para ficar acessível no handlePiP
  const webSource = useMemo<VideoSource | null>(() => {
    if (!videoId) return null;
    return isDrive
      ? { html: buildDriveHTML(videoId), baseUrl: 'https://drive.google.com' }
      : { html: buildYouTubeHTML(videoId), baseUrl: 'https://www.youtube-nocookie.com' };
  }, [videoId, isDrive]);

  // PiP: delega ao PipProvider (sobrevive à navegação)
  const handlePiP = useCallback(() => {
    if (!webSource) return;
    if (isPip) stopPip();
    else startPip(webSource, titulo);
  }, [webSource, isPip, startPip, stopPip, titulo]);

  const videoH   = fullscreen ? screenH : cinema ? CINEMA_H : NORMAL_H;
  const progress = duration > 0 ? Math.min(currentTime / duration, 1) : 0;
  const fillW    = progWidth * progress;

  // ── Em Produção ──────────────────────────────────────────────────────────
  if (!videoId) {
    return (
      <View style={[styles.container, { backgroundColor: theme.bg }]}>
        <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
        <View style={[styles.header, { borderBottomColor: theme.border, backgroundColor: theme.bg }]}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} hitSlop={{ top: 14, bottom: 14, left: 14, right: 14 }}
            accessibilityRole="button"
            accessibilityLabel="Voltar"
          >
            <Ionicons name="arrow-back" size={24} color={theme.text} />
          </TouchableOpacity>
          <View style={styles.headerMid}>
            <Text style={[styles.materiaLabel, { color: ACCENT }]}>{materiaNome}</Text>
            <Text style={[styles.aulaTitle,    { color: theme.text }]} numberOfLines={2}>{titulo}</Text>
          </View>
        </View>
        <View style={styles.center}>
          <MaterialCommunityIcons name="wrench-clock" size={64} color="#F59E0B" />
          <Text style={[styles.prodTitle, { color: theme.text }]}>Em Produção</Text>
          <Text style={[styles.prodSub,   { color: theme.sub  }]}>
            Esta aula está sendo preparada pela equipe Nivelis.{'\n'}Em breve estará disponível!
          </Text>
        </View>
        <NivelisModal {...modal} />
      </View>
    );
  }

  // webSource já calculado via useMemo acima (não pode ser null aqui pois videoId !== null)

  // ── Player ───────────────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: '#000' }]}>
      <StatusBar barStyle="light-content" backgroundColor="#000" />

      {/* Header — oculto no cinema e fullscreen */}
      {!cinema && !fullscreen && (
        <View style={[styles.header, { borderBottomColor: '#222', backgroundColor: '#000' }]}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn} hitSlop={{ top: 14, bottom: 14, left: 14, right: 14 }}
            accessibilityRole="button"
            accessibilityLabel="Voltar"
          >
            <Ionicons name="arrow-back" size={24} color="#FFF" />
          </TouchableOpacity>
          <View style={styles.headerMid}>
            <Text style={[styles.materiaLabel, { color: ACCENT }]}>{materiaNome}</Text>
            <Text style={[styles.aulaTitle,    { color: '#FFF' }]} numberOfLines={1}>{titulo}</Text>
          </View>
        </View>
      )}

      {/* ── Player box ── */}
      <View style={[styles.playerBox, { height: videoH }]}>
        <WebView
          ref={webRef}
          source={webSource!}
          incognito
          style={styles.webview}
          allowsFullscreenVideo
          allowsInlineMediaPlayback
          allowsPictureInPictureMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          javaScriptEnabled
          domStorageEnabled
          originWhitelist={['*']}
          mixedContentMode="always"
          onMessage={onMessage}
          onLoadStart={() => { setLoading(true); setErro(false); }}
          onLoadEnd={() => setLoading(false)}
          onError={() => { setLoading(false); setErro(true); }}
        />

        {/* Loading */}
        {loading && !erro && (
          <View style={styles.overlay} pointerEvents="none">
            <ActivityIndicator size="large" color={ACCENT} />
            <Text style={styles.loadingText}>Carregando vídeo…</Text>
          </View>
        )}

        {/* Erro */}
        {erro && (
          <View style={styles.overlay}>
            <MaterialCommunityIcons name="wifi-off" size={48} color="#888" />
            <Text style={styles.erroTitle}>Não foi possível carregar</Text>
            <Text style={styles.erroSub}>Verifique sua conexão e tente novamente</Text>
            <TouchableOpacity
              style={[styles.retryBtn, { backgroundColor: ACCENT }]}
              onPress={() => { setErro(false); setLoading(true); webRef.current?.reload(); }}
            >
              <Ionicons name="refresh" size={16} color="#FFF" />
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── Controles overlay ── */}
        {!erro && (
          <View style={styles.controls} pointerEvents="box-none">

            {/* Barra de progresso */}
            <View style={styles.progressRow} pointerEvents="box-none">
              <Text style={styles.timeText}>{fmtTime(currentTime)}</Text>
              <TouchableOpacity
                style={styles.progressTouchable}
                onLayout={e => setProgWidth(e.nativeEvent.layout.width || 1)}
                onPress={e => seekTo(e.nativeEvent.locationX / progWidth)}
                activeOpacity={1}
              >
                <View style={styles.progressBg}>
                  <View style={[styles.progressFill, { width: fillW }]} />
                </View>
              </TouchableOpacity>
              <Text style={styles.timeText}>{fmtTime(duration)}</Text>
            </View>

            {/* Linha de botões */}
            <View style={styles.btnRow} pointerEvents="box-none">

              {/* Centro: seek + play (flex:1, centralizado) */}
              <View style={styles.mainControls} pointerEvents="box-none">
                <TouchableOpacity onPress={() => seekRelative(-10)} style={styles.ctrlBtn}>
                  <Ionicons name="play-back" size={22} color="#FFF" />
                  <Text style={styles.seekLabel}>10s</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={togglePlay}
                                  accessibilityRole="button"
                                  accessibilityLabel={playing ? "Pausar a aula" : "Reproduzir a aula"}>
                  <Ionicons name={playing ? 'pause-circle' : 'play-circle'} size={52} color="#FFF" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => seekRelative(10)} style={styles.ctrlBtn}>
                  <Ionicons name="play-forward" size={22} color="#FFF" />
                  <Text style={styles.seekLabel}>10s</Text>
                </TouchableOpacity>
              </View>

              {/* Direita: modos */}
              <View style={styles.modeGroup} pointerEvents="box-none">
                <TouchableOpacity onPress={handlePiP} style={styles.modeBtn}
                                    accessibilityRole="button"
                                    accessibilityLabel={isPip ? "Sair do modo janela flutuante" : "Assistir em janela flutuante"}
                                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                  <MaterialCommunityIcons
                    name="picture-in-picture-bottom-right"
                    size={20}
                    color={isPip ? ACCENT : '#FFF'}
                  />
                </TouchableOpacity>
                <TouchableOpacity onPress={toggleCinema} style={styles.modeBtn}
                                    accessibilityRole="button"
                                    accessibilityLabel={cinema ? "Sair do modo cinema" : "Modo cinema"}
                                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                  <MaterialCommunityIcons
                    name={cinema ? 'movie-open-off' : 'movie-open'}
                    size={20}
                    color={cinema ? ACCENT : '#FFF'}
                  />
                </TouchableOpacity>
                <TouchableOpacity onPress={handleFullscreen} style={styles.modeBtn}
                                    accessibilityRole="button"
                                    accessibilityLabel={fullscreen ? "Sair da tela cheia" : "Tela cheia"}
                                    hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                  <MaterialCommunityIcons
                    name={fullscreen ? 'fullscreen-exit' : 'fullscreen'}
                    size={20}
                    color={fullscreen ? ACCENT : '#FFF'}
                  />
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}
      </View>

      {/* ── Info (oculta no cinema e fullscreen) ── */}
      {!cinema && !fullscreen && (
        <ScrollView
          style={{ flex: 1, backgroundColor: theme.bg }}
          contentContainerStyle={styles.info}
          showsVerticalScrollIndicator={false}
        >
          <Text style={[styles.infoTitle, { color: theme.text }]}>{titulo}</Text>
          <View style={styles.metaRow}>
            <View style={styles.metaItem}>
              <Ionicons name="time-outline" size={15} color={theme.sub} />
              <Text style={[styles.metaText, { color: theme.sub }]}>{duracao}</Text>
            </View>
            <View style={styles.metaItem}>
              <FontAwesome5 name={isDrive ? 'google-drive' : 'youtube'} size={13} color={theme.sub} />
              <Text style={[styles.metaText, { color: theme.sub }]}>{isDrive ? 'Google Drive' : 'YouTube'}</Text>
            </View>
          </View>
          <View style={[styles.divider, { backgroundColor: theme.border }]} />
          <Text style={[styles.descLabel, { color: theme.sub }]}>SOBRE ESTA AULA</Text>
          <Text style={[styles.descText,  { color: theme.text }]}>
            Assista à aula completa de {titulo}, parte do módulo {materiaNome}.{'\n'}
            Use os controles para pausar, retroceder ou avançar 10 segundos.
          </Text>
        </ScrollView>
      )}

      <NivelisModal {...modal} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 55,
    paddingBottom: 14,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
  },
  backBtn:      { marginRight: 12, padding: 4 },
  headerMid:    { flex: 1 },
  materiaLabel: { fontSize: 10, fontWeight: 'bold', letterSpacing: 1, marginBottom: 2 },
  aulaTitle:    { fontSize: 15, fontWeight: 'bold' },

  playerBox: { width: '100%', backgroundColor: '#000', position: 'relative' },
  webview:   { flex: 1, backgroundColor: '#000' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: { color: '#888', fontSize: 13 },
  erroTitle:   { color: '#FFF', fontSize: 16, fontWeight: 'bold' },
  erroSub:     { color: '#888', fontSize: 13, textAlign: 'center', paddingHorizontal: 32 },
  retryBtn:    {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingHorizontal: 20, paddingVertical: 10, borderRadius: 12, marginTop: 4,
  },
  retryText: { color: '#FFF', fontSize: 14, fontWeight: 'bold' },

  // ── Controles overlay ──
  controls: {
    position: 'absolute',
    bottom: 0, left: 0, right: 0,
    backgroundColor: 'rgba(0,0,0,0.65)',
    paddingTop: 6,
    paddingBottom: 10,
    gap: 2,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 8,
  },
  timeText:          { color: '#FFF', fontSize: 11, minWidth: 34, textAlign: 'center' },
  progressTouchable: { flex: 1, paddingVertical: 10, justifyContent: 'center' },
  progressBg:        { height: 3, backgroundColor: 'rgba(255,255,255,0.30)', borderRadius: 2, overflow: 'hidden' },
  progressFill:      { height: 3, backgroundColor: ACCENT, borderRadius: 2 },

  btnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingTop: 2,
  },
  mainControls: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
  },
  ctrlBtn:  { alignItems: 'center', gap: 2 },
  seekLabel:{ color: '#FFF', fontSize: 10 },
  modeGroup:{ flexDirection: 'row', alignItems: 'center' },
  modeBtn:  { padding: 7 },

  // ── Info ──
  info:      { padding: 20, paddingBottom: 50, gap: 10 },
  infoTitle: { fontSize: 18, fontWeight: 'bold' },
  metaRow:   { flexDirection: 'row', gap: 20 },
  metaItem:  { flexDirection: 'row', alignItems: 'center', gap: 6 },
  metaText:  { fontSize: 13 },
  divider:   { height: 1, marginVertical: 4 },
  descLabel: { fontSize: 10, fontWeight: 'bold', letterSpacing: 1 },
  descText:  { fontSize: 14, lineHeight: 22 },

  center:    { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12, padding: 32 },
  prodTitle: { fontSize: 20, fontWeight: 'bold' },
  prodSub:   { fontSize: 14, textAlign: 'center', lineHeight: 22 },
});
