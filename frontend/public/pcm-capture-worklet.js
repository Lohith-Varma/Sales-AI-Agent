class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffers = [];
    this.sampleCount = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const copy = input[0].slice();
      this.buffers.push(copy);
      this.sampleCount += copy.length;
      // Batch the 128-sample render quanta before main-thread resampling. This
      // avoids hundreds of messages per second and tiny-block rounding drift.
      if (this.sampleCount >= 1024) {
        const merged = new Float32Array(this.sampleCount);
        let offset = 0;
        for (const buffer of this.buffers) {
          merged.set(buffer, offset);
          offset += buffer.length;
        }
        this.buffers = [];
        this.sampleCount = 0;
        this.port.postMessage(merged.buffer, [merged.buffer]);
      }
    }
    return true;
  }
}

registerProcessor("pcm-capture-processor", PcmCaptureProcessor);
