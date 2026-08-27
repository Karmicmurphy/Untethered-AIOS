(() => {
  "use strict";
  const TRACKS = ["kick", "snare", "closedHat", "openHat", "percussion", "synth"];
  const LOOP_SLOTS = ["loop-1", "loop-2", "loop-3", "loop-4"];
  const SCALE = [0, 2, 3, 5, 7, 8, 10, 12];
  const clamp = (value, low, high) => Math.max(low, Math.min(high, Number(value)));

  function noiseBuffer(context, seconds = 0.35) {
    const length = Math.max(1, Math.ceil(context.sampleRate * seconds));
    const buffer = context.createBuffer(1, length, context.sampleRate);
    const data = buffer.getChannelData(0);
    let seed = 0x54574953;
    for (let index = 0; index < data.length; index += 1) {
      seed = (1664525 * seed + 1013904223) >>> 0;
      data[index] = ((seed / 0xffffffff) * 2 - 1) * (1 - index / data.length);
    }
    return buffer;
  }

  function envelope(gain, when, peak, duration) {
    gain.gain.cancelScheduledValues(when);
    gain.gain.setValueAtTime(Math.max(0.0001, peak), when);
    gain.gain.exponentialRampToValueAtTime(0.0001, when + duration);
  }

  function triggerVoice(context, track, when, destination, noteValue = 1, velocity = 1) {
    const level = clamp(velocity, 0.05, 1);
    if (track === "kick") {
      const oscillator = context.createOscillator(), gain = context.createGain();
      oscillator.type = "sine"; oscillator.frequency.setValueAtTime(145, when); oscillator.frequency.exponentialRampToValueAtTime(43, when + 0.16);
      envelope(gain, when, 0.88 * level, 0.2); oscillator.connect(gain).connect(destination); oscillator.start(when); oscillator.stop(when + 0.22); return;
    }
    if (track === "snare") {
      const noise = context.createBufferSource(), filter = context.createBiquadFilter(), gain = context.createGain();
      noise.buffer = noiseBuffer(context, 0.2); filter.type = "highpass"; filter.frequency.value = 1100; envelope(gain, when, 0.48 * level, 0.18);
      noise.connect(filter).connect(gain).connect(destination); noise.start(when); noise.stop(when + 0.2);
      const body = context.createOscillator(), bodyGain = context.createGain(); body.type = "triangle"; body.frequency.value = 185; envelope(bodyGain, when, 0.18 * level, 0.11); body.connect(bodyGain).connect(destination); body.start(when); body.stop(when + 0.13); return;
    }
    if (track === "closedHat" || track === "openHat") {
      const duration = track === "openHat" ? 0.28 : 0.065;
      const noise = context.createBufferSource(), high = context.createBiquadFilter(), gain = context.createGain();
      noise.buffer = noiseBuffer(context, duration); high.type = "highpass"; high.frequency.value = track === "openHat" ? 5200 : 6900; envelope(gain, when, (track === "openHat" ? 0.18 : 0.14) * level, duration);
      noise.connect(high).connect(gain).connect(destination); noise.start(when); noise.stop(when + duration); return;
    }
    if (track === "percussion") {
      const oscillator = context.createOscillator(), gain = context.createGain(); oscillator.type = "triangle"; oscillator.frequency.setValueAtTime(510, when); oscillator.frequency.exponentialRampToValueAtTime(220, when + 0.09); envelope(gain, when, 0.22 * level, 0.11); oscillator.connect(gain).connect(destination); oscillator.start(when); oscillator.stop(when + 0.12); return;
    }
    const root = 48, degree = SCALE[Math.max(0, Math.min(7, Number(noteValue) - 1))] || 0;
    const oscillator = context.createOscillator(), filter = context.createBiquadFilter(), gain = context.createGain();
    oscillator.type = "sawtooth"; oscillator.frequency.value = 440 * Math.pow(2, (root + degree - 69) / 12); filter.type = "lowpass"; filter.frequency.value = 1400; envelope(gain, when, 0.17 * level, 0.24); oscillator.connect(filter).connect(gain).connect(destination); oscillator.start(when); oscillator.stop(when + 0.26);
  }

  function makeGraph(context, destination, mixer, withMeter = false) {
    const master = context.createGain(); master.gain.value = clamp(mixer.master ?? 0.85, 0, 1); master.connect(destination);
    const analyser = withMeter ? context.createAnalyser() : null;
    if (analyser) { analyser.fftSize = 256; master.disconnect(); master.connect(analyser).connect(destination); }
    const soloed = TRACKS.some(track => mixer.tracks?.[track]?.solo);
    const outputs = {};
    for (const track of TRACKS) {
      const gain = context.createGain(), value = mixer.tracks?.[track] || {};
      gain.gain.value = value.muted || (soloed && !value.solo) ? 0 : clamp(value.volume ?? 0.75, 0, 1);
      gain.connect(master); outputs[track] = gain;
    }
    return {master, analyser, outputs};
  }

  function makeLoopGraph(context, master, slot) {
    const input = context.createGain(), filter = context.createBiquadFilter(), dry = context.createGain(), delay = context.createDelay(2), feedback = context.createGain(), wet = context.createGain(), pan = context.createStereoPanner(), output = context.createGain();
    filter.type = "lowpass";
    input.connect(filter); filter.connect(dry).connect(pan); filter.connect(delay).connect(wet).connect(pan); delay.connect(feedback).connect(delay); pan.connect(output).connect(master);
    const graph = {input, filter, dry, delay, feedback, wet, pan, output};
    applyLoopGraph(graph, slot, context.currentTime, false);
    return graph;
  }

  function applyLoopGraph(graph, slot, when, soloSuppressed) {
    const effects = slot.effects || {};
    graph.filter.frequency.setTargetAtTime(clamp(effects.filterHz ?? 18000, 240, 18000), when, 0.01);
    graph.delay.delayTime.setTargetAtTime(clamp(effects.echoTime ?? 0.25, 0.05, 0.75), when, 0.01);
    graph.feedback.gain.setTargetAtTime(clamp(effects.echo ?? 0, 0, 0.6), when, 0.01);
    graph.wet.gain.setTargetAtTime(clamp(effects.echo ?? 0, 0, 0.5), when, 0.01);
    graph.dry.gain.setTargetAtTime(1, when, 0.01);
    graph.pan.pan.setTargetAtTime(clamp(slot.pan ?? 0, -1, 1), when, 0.01);
    graph.output.gain.setTargetAtTime(slot.muted || soloSuppressed ? 0 : clamp(slot.gain ?? 0.75, 0, 1), when, 0.01);
  }

  function arrangementFor(state) {
    const ordered = state.songMode ? (state.arrangement || []).filter(value => state.patterns?.[value]) : [state.activePattern || "A"];
    return ordered.length ? ordered : [state.activePattern || "A"];
  }

  function schedulePattern(context, graph, pattern, start, secondsPerStep) {
    for (let step = 0; step < 16; step += 1) {
      const when = start + step * secondsPerStep;
      for (const track of TRACKS) {
        const value = Number(pattern?.tracks?.[track]?.[step] || 0);
        if (value > 0) triggerVoice(context, track, when, graph.outputs[track], value, 1);
      }
    }
  }

  function encodeWav(buffer) {
    const channels = buffer.numberOfChannels, frames = buffer.length;
    const output = new ArrayBuffer(44 + frames * channels * 2), view = new DataView(output); let offset = 0;
    const text = value => { for (const character of value) view.setUint8(offset++, character.charCodeAt(0)); };
    text("RIFF"); view.setUint32(offset, 36 + frames * channels * 2, true); offset += 4; text("WAVEfmt "); view.setUint32(offset, 16, true); offset += 4;
    view.setUint16(offset, 1, true); offset += 2; view.setUint16(offset, channels, true); offset += 2; view.setUint32(offset, buffer.sampleRate, true); offset += 4;
    view.setUint32(offset, buffer.sampleRate * channels * 2, true); offset += 4; view.setUint16(offset, channels * 2, true); offset += 2; view.setUint16(offset, 16, true); offset += 2;
    text("data"); view.setUint32(offset, frames * channels * 2, true); offset += 4;
    for (let frame = 0; frame < frames; frame += 1) for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, buffer.getChannelData(channel)[frame])); view.setInt16(offset, sample < 0 ? sample * 32768 : sample * 32767, true); offset += 2;
    }
    return output;
  }

  class MusicEngine {
    constructor(getState, callbacks = {}) { this.getState = getState; this.callbacks = callbacks; this.context = null; this.graph = null; this.loopGraphs = new Map(); this.loopBuffers = new Map(); this.loopSources = new Map(); this.pendingSources = new Map(); this.timer = null; this.step = 0; this.arrangementIndex = 0; this.nextTime = 0; this.transportOrigin = 0; this.playing = false; this.paused = false; this.meterFrame = 0; }
    async ensure() {
      if (!this.context) {
        const Context = window.AudioContext || window.webkitAudioContext;
        if (!Context) throw new Error("Web Audio is unavailable");
        this.context = new Context({latencyHint: "interactive"});
        this.graph = makeGraph(this.context, this.context.destination, this.getState().mixer, true);
        for (const slot of this.getState().loopDeck?.slots || []) this.loopGraphs.set(slot.slotId, makeLoopGraph(this.context, this.graph.master, slot));
      }
      if (this.context.state === "suspended") await this.context.resume(); this.updateMixer(); return this.context;
    }
    async decodeLoop(slotId, bytes) { const context = await this.ensure(); const buffer = await context.decodeAudioData(bytes.slice(0)); this.loopBuffers.set(slotId, buffer); this.callbacks.onLoopLoaded?.(slotId, {duration: buffer.duration, channels: buffer.numberOfChannels, sampleRate: buffer.sampleRate}); return buffer; }
    hasLoop(slotId) { return this.loopBuffers.has(slotId); }
    copyLoopBuffer(sourceSlotId, targetSlotId) { const buffer = this.loopBuffers.get(sourceSlotId); if (buffer) this.loopBuffers.set(targetSlotId, buffer); }
    unloadLoop(slotId) { this.stopLoop(slotId, "immediate"); this.loopBuffers.delete(slotId); }
    updateMixer() {
      if (!this.graph) return;
      const state = this.getState(), mixer = state.mixer, soloed = TRACKS.some(track => mixer.tracks[track].solo);
      this.graph.master.gain.setTargetAtTime(clamp(mixer.master, 0, 1), this.context.currentTime, 0.01);
      for (const track of TRACKS) { const value = mixer.tracks[track]; this.graph.outputs[track].gain.setTargetAtTime(value.muted || (soloed && !value.solo) ? 0 : clamp(value.volume, 0, 1), this.context.currentTime, 0.01); }
      const loopSlots = state.loopDeck?.slots || [], loopSoloed = loopSlots.some(slot => slot.solo);
      for (const slot of loopSlots) {
        if (!this.loopGraphs.has(slot.slotId)) this.loopGraphs.set(slot.slotId, makeLoopGraph(this.context, this.graph.master, slot));
        applyLoopGraph(this.loopGraphs.get(slot.slotId), slot, this.context.currentTime, loopSoloed && !slot.solo);
      }
    }
    beatPosition(at = this.context?.currentTime || 0) { const bpm = clamp(this.getState().bpm, 50, 220); return this.playing ? Math.max(0, (at - this.transportOrigin) / (60 / bpm)) : this.step / 4; }
    quantizedTime(mode = "bar") { const now = this.context.currentTime + 0.01; if (!this.playing || mode === "immediate") return now; const beatSeconds = 60 / clamp(this.getState().bpm, 50, 220), beat = Math.max(0, (now - this.transportOrigin) / beatSeconds), quantum = mode === "beat" ? 1 : 4, targetBeat = Math.ceil((beat + 0.001) / quantum) * quantum; return this.transportOrigin + targetBeat * beatSeconds; }
    async trigger(track, note = 1) { await this.ensure(); triggerVoice(this.context, track, this.context.currentTime + 0.005, this.graph.outputs[track], note, 1); this.callbacks.onHit?.(track); this.startMeter(); }
    async launchLoop(slotId, mode = "bar") {
      await this.ensure(); const buffer = this.loopBuffers.get(slotId); if (!buffer) throw new Error("Load a governed WAV loop into this slot first");
      const slot = this.getState().loopDeck.slots.find(value => value.slotId === slotId); if (!slot) throw new Error("Loop slot is unavailable");
      const when = this.quantizedTime(mode), prior = this.loopSources.get(slotId), pending = this.pendingSources.get(slotId); try { pending?.stop(); } catch {}
      const source = this.context.createBufferSource(); source.buffer = buffer; source.loop = true; source.playbackRate.value = clamp(this.getState().bpm / clamp(slot.bpm, 30, 300), 0.25, 4); source.connect(this.loopGraphs.get(slotId).input); source.start(when); if (prior) { try { prior.stop(when); } catch {} }
      this.pendingSources.set(slotId, source); const delay = Math.max(0, (when - this.context.currentTime) * 1000); setTimeout(() => { if (this.pendingSources.get(slotId) === source) { this.pendingSources.delete(slotId); this.loopSources.set(slotId, source); this.callbacks.onLoopState?.(slotId, "playing", mode); } }, delay);
      this.callbacks.onLoopQueued?.(slotId, mode, this.beatPosition(when)); this.startMeter(); return {slotId, mode, when, beat:this.beatPosition(when)};
    }
    stopLoop(slotId, mode = "bar") { if (!this.context) return; const when = this.quantizedTime(mode), sources = [this.pendingSources.get(slotId), this.loopSources.get(slotId)].filter(Boolean); for (const source of sources) { try { source.stop(when); } catch {} } const delay = Math.max(0, (when - this.context.currentTime) * 1000); setTimeout(() => { this.pendingSources.delete(slotId); this.loopSources.delete(slotId); this.callbacks.onLoopState?.(slotId, "stopped", mode); }, delay); this.callbacks.onLoopQueued?.(slotId, `stop-${mode}`, this.beatPosition(when)); }
    stopAllLoops(mode = "immediate") { for (const slotId of LOOP_SLOTS) this.stopLoop(slotId, mode); }
    startMeter() { if (!this.graph?.analyser || this.meterFrame) return; const data = new Uint8Array(this.graph.analyser.fftSize); const draw = () => { if (!this.graph?.analyser) { this.meterFrame = 0; return; } this.graph.analyser.getByteTimeDomainData(data); let sum = 0; for (const value of data) { const sample = (value - 128) / 128; sum += sample * sample; } this.callbacks.onMeter?.(Math.min(1, Math.sqrt(sum / data.length) * 3)); this.meterFrame = requestAnimationFrame(draw); }; draw(); }
    async play() { await this.ensure(); if (this.playing) return; this.playing = true; this.paused = false; this.nextTime = this.context.currentTime + 0.05; this.transportOrigin = this.nextTime - (this.step / 4) * (60 / clamp(this.getState().bpm, 50, 220)); this.timer = setInterval(() => this.scheduler(), 25); this.startMeter(); this.callbacks.onState?.("playing"); }
    scheduler() { const state = this.getState(), patterns = arrangementFor(state), seconds = 60 / clamp(state.bpm, 50, 220) / 4; this.updateMixer(); while (this.playing && this.nextTime < this.context.currentTime + 0.1) { const key = patterns[this.arrangementIndex] || state.activePattern; const pattern = state.patterns[key]; for (const track of TRACKS) { const value = Number(pattern.tracks[track][this.step] || 0); if (value > 0) triggerVoice(this.context, track, this.nextTime, this.graph.outputs[track], value, 1); } this.callbacks.onStep?.(this.step, key, this.arrangementIndex); this.nextTime += seconds; this.step += 1; if (this.step >= 16) { this.step = 0; this.arrangementIndex += 1; if (this.arrangementIndex >= patterns.length) { if (state.loop) this.arrangementIndex = 0; else { this.stop(); break; } } } } }
    pause() { if (!this.playing) return; clearInterval(this.timer); this.timer = null; this.playing = false; this.paused = true; this.stopAllLoops("immediate"); this.callbacks.onState?.("paused"); }
    stop() { clearInterval(this.timer); this.timer = null; this.playing = false; this.paused = false; this.step = 0; this.arrangementIndex = 0; this.stopAllLoops("immediate"); this.callbacks.onStep?.(-1, null, -1); this.callbacks.onState?.("stopped"); }
    async render(state) {
      const sampleRate = 44100, patterns = arrangementFor(state), seconds = 60 / clamp(state.bpm, 50, 220) / 4, patternDuration = patterns.length * 16 * seconds;
      const loadedSlots = (state.loopDeck?.slots || []).filter(slot => this.loopBuffers.has(slot.slotId));
      const capturedBeats = Number(state.loopDeck?.performance?.durationBeats || 0), loopDuration = loadedSlots.reduce((max, slot) => Math.max(max, slot.bars * 4 * 60 / clamp(state.bpm, 50, 220)), 0), duration = Math.max(patternDuration, capturedBeats * 60 / clamp(state.bpm, 50, 220), loopDuration, 1) + 0.35;
      const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext; if (!Offline) throw new Error("Offline Web Audio rendering is unavailable");
      const context = new Offline(2, Math.ceil(sampleRate * duration), sampleRate), graph = makeGraph(context, context.destination, state.mixer, false);
      patterns.forEach((key, index) => schedulePattern(context, graph, state.patterns[key], index * 16 * seconds, seconds));
      for (const slot of loadedSlots) { const loopGraph = makeLoopGraph(context, graph.master, slot), source = context.createBufferSource(); source.buffer = this.loopBuffers.get(slot.slotId); source.loop = true; source.playbackRate.value = clamp(state.bpm / clamp(slot.bpm, 30, 300), 0.25, 4); source.connect(loopGraph.input); source.start(0); source.stop(Math.max(0.01, duration - 0.35)); }
      const buffer = await context.startRendering(), wav = encodeWav(buffer); let peak = 0, energy = 0; const data = buffer.getChannelData(0); for (const value of data) { const absolute = Math.abs(value); if (absolute > peak) peak = absolute; energy += value * value; }
      return {buffer, wav, evidence:{schemaVersion:"music-render-evidence-v2",patterns,loopArtifactIds:loadedSlots.map(slot=>slot.artifactId).filter(Boolean),seconds:Number(duration.toFixed(3)),sampleRate,channels:2,frames:buffer.length,bytes:wav.byteLength,peak:Number(peak.toFixed(6)),rms:Number(Math.sqrt(energy / data.length).toFixed(6)),nonSilent:peak > 0.0001,header:String.fromCharCode(...new Uint8Array(wav.slice(0,4)))}};
    }
    dispose() { this.stop(); if (this.meterFrame) cancelAnimationFrame(this.meterFrame); this.meterFrame = 0; this.context?.close(); this.context = null; this.graph = null; this.loopGraphs.clear(); this.loopBuffers.clear(); }
  }
  window.TwisMusicEngine = {MusicEngine, TRACKS, LOOP_SLOTS, SCALE, encodeWav, triggerVoice, arrangementFor};
})();
