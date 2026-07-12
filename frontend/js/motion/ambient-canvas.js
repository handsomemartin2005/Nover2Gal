class AmbientCanvas {
  constructor() {
    this.canvas = null;
    this.context = null;
    this.frame = 0;
    this.particles = [];
    this.pointer = { x: -1000, y: -1000 };
    this.running = false;
    this.cleanups = [];
  }

  mount({ workspace = false } = {}) {
    this.unmount();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "reduced";
    if (reduced) return;
    const backdrop = document.querySelector(".ambient-backdrop");
    if (!backdrop) return;
    this.canvas = document.createElement("canvas");
    this.canvas.className = `ambient-canvas${workspace ? " ambient-canvas--workspace" : ""}`;
    this.canvas.setAttribute("aria-hidden", "true");
    backdrop.append(this.canvas);
    this.context = this.canvas.getContext("2d");
    const resize = () => this.resize(workspace);
    const pointer = (event) => { this.pointer.x = event.clientX; this.pointer.y = event.clientY; };
    const visibility = () => { this.running = !document.hidden; if (this.running) this.loop(); };
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", pointer, { passive: true });
    document.addEventListener("visibilitychange", visibility);
    this.cleanups.push(() => window.removeEventListener("resize", resize), () => window.removeEventListener("pointermove", pointer), () => document.removeEventListener("visibilitychange", visibility));
    resize();
    this.running = true;
    this.loop();
  }

  resize(workspace) {
    if (!this.canvas || !this.context) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.canvas.width = Math.floor(width * dpr);
    this.canvas.height = Math.floor(height * dpr);
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;
    this.context.setTransform(dpr, 0, 0, dpr, 0, 0);
    const mobile = width < 768;
    const level = document.documentElement.dataset.motion || "balanced";
    const count = workspace ? (mobile ? 8 : 16) : mobile ? 14 : level === "full" ? 54 : 38;
    this.particles = Array.from({ length: count }, (_, index) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      radius: index % 11 === 0 ? 2.2 : Math.random() * 1.3 + .35,
      speed: Math.random() * .12 + .025,
      drift: (Math.random() - .5) * .09,
      alpha: Math.random() * .42 + .12,
      hue: index % 4 === 0 ? 274 : 171,
    }));
  }

  loop() {
    if (!this.running || !this.canvas || !this.context || this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      if (!this.running) return;
      const ctx = this.context;
      const width = window.innerWidth;
      const height = window.innerHeight;
      ctx.clearRect(0, 0, width, height);
      this.particles.forEach((particle, index) => {
        const dx = particle.x - this.pointer.x;
        const dy = particle.y - this.pointer.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 120 && distance > 0) {
          const force = (120 - distance) / 120 * .14;
          particle.x += dx / distance * force;
          particle.y += dy / distance * force;
        }
        particle.y -= particle.speed;
        particle.x += particle.drift;
        if (particle.y < -8) { particle.y = height + 8; particle.x = Math.random() * width; }
        if (particle.x < -8) particle.x = width + 8;
        if (particle.x > width + 8) particle.x = -8;
        ctx.beginPath();
        ctx.fillStyle = `hsla(${particle.hue}, 78%, 75%, ${particle.alpha})`;
        ctx.shadowBlur = particle.radius > 1.8 ? 10 : 0;
        ctx.shadowColor = `hsla(${particle.hue}, 80%, 70%, .4)`;
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fill();
        if (index > 0 && index % 17 === 0) {
          const previous = this.particles[index - 1];
          ctx.beginPath();
          ctx.strokeStyle = "rgba(85,234,219,.055)";
          ctx.lineWidth = .6;
          ctx.moveTo(previous.x, previous.y);
          ctx.lineTo(particle.x, particle.y);
          ctx.stroke();
        }
      });
      ctx.shadowBlur = 0;
      this.loop();
    });
  }

  unmount() {
    this.running = false;
    if (this.frame) cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.cleanups.splice(0).forEach((cleanup) => cleanup());
    this.canvas?.remove();
    this.canvas = null;
    this.context = null;
  }
}

export const ambientCanvas = new AmbientCanvas();

