// Thin wrapper around browser Web Speech API with EN + ZH voice selection.
let voicesCache = null;

export function loadVoices() {
  return new Promise((resolve) => {
    if (!("speechSynthesis" in window)) return resolve([]);
    if (voicesCache && voicesCache.length) return resolve(voicesCache);
    const existing = window.speechSynthesis.getVoices();
    if (existing && existing.length) {
      voicesCache = existing;
      return resolve(existing);
    }
    const handler = () => {
      voicesCache = window.speechSynthesis.getVoices();
      resolve(voicesCache || []);
    };
    window.speechSynthesis.onvoiceschanged = handler;
    // Fallback timeout
    setTimeout(() => {
      if (!voicesCache) {
        voicesCache = window.speechSynthesis.getVoices() || [];
        resolve(voicesCache);
      }
    }, 800);
  });
}

export function pickVoice(voices, lang, preferredName) {
  if (!voices || !voices.length) return null;
  if (preferredName) {
    const v = voices.find((x) => x.name === preferredName);
    if (v) return v;
  }
  const target = lang === "zh" ? "zh" : "en";
  const exact = voices.find((v) => v.lang?.toLowerCase().startsWith(target));
  return exact || voices[0];
}

export function speak(text, { lang = "en", voiceName } = {}) {
  if (!("speechSynthesis" in window)) return;
  stop();
  return loadVoices().then((voices) => {
    const u = new SpeechSynthesisUtterance(text);
    const v = pickVoice(voices, lang, voiceName);
    if (v) u.voice = v;
    u.lang = v?.lang || (lang === "zh" ? "zh-CN" : "en-US");
    u.rate = 1.0;
    u.pitch = 1.0;
    window.speechSynthesis.speak(u);
    return u;
  });
}

export function pause() {
  if ("speechSynthesis" in window) window.speechSynthesis.pause();
}
export function resume() {
  if ("speechSynthesis" in window) window.speechSynthesis.resume();
}
export function stop() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}
