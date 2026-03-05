/**
 * AudioWorklet processor for capturing PCM 16kHz mono audio.
 *
 * Runs in a dedicated audio thread. Receives raw float32 samples from
 * getUserMedia, converts to 16-bit PCM, and posts binary ArrayBuffers
 * to the main thread via the port.
 *
 * The main thread forwards these buffers as binary WebSocket frames.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this._buffer = [];
        // Target ~100ms chunks at 16kHz = 1600 samples = 3200 bytes
        this._targetSamples = 1600;
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || !input[0]) return true;

        const channelData = input[0]; // mono channel

        // Accumulate samples
        for (let i = 0; i < channelData.length; i++) {
            this._buffer.push(channelData[i]);
        }

        // When we have enough samples, convert and send
        while (this._buffer.length >= this._targetSamples) {
            const chunk = this._buffer.splice(0, this._targetSamples);
            const pcm16 = new Int16Array(chunk.length);

            for (let i = 0; i < chunk.length; i++) {
                // Clamp to [-1, 1] and convert to 16-bit signed integer
                const s = Math.max(-1, Math.min(1, chunk[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        }

        return true;
    }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
