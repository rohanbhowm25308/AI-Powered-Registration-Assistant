/* ============ LIVE PARTICLE NETWORK BACKGROUND ============
   Layered: soft drifting nebula glows behind, a denser node network
   in front, and gentle mouse-reactive parallax so the background
   actually reads as "alive" instead of a faint static texture. */
(function () {
  const canvas = document.getElementById('particleCanvas');
  const ctx = canvas.getContext('2d');
  let w, h, nodes = [], blobs = [];
  const NODE_COUNT_BASE = 110; // scaled by screen area below
  const mouse = { x: null, y: null, active: false };

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true;
  });
  window.addEventListener('mouseleave', () => { mouse.active = false; });

  function rand(a, b) { return a + Math.random() * (b - a); }

  class Blob {
    constructor() {
      this.x = rand(0, w); this.y = rand(0, h);
      this.r = rand(220, 420);
      this.vx = rand(-0.06, 0.06); this.vy = rand(-0.06, 0.06);
      this.hue = Math.random() < 0.5 ? [79, 224, 255] : [61, 107, 240];
      this.alpha = rand(0.05, 0.1);
    }
    step() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < -this.r) this.x = w + this.r;
      if (this.x > w + this.r) this.x = -this.r;
      if (this.y < -this.r) this.y = h + this.r;
      if (this.y > h + this.r) this.y = -this.r;
    }
    draw() {
      const [r, g, b] = this.hue;
      const grad = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.r);
      grad.addColorStop(0, `rgba(${r},${g},${b},${this.alpha})`);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  class Node {
    constructor() {
      this.x = rand(0, w); this.y = rand(0, h);
      this.baseX = this.x; this.baseY = this.y;
      this.vx = rand(-0.18, 0.18); this.vy = rand(-0.18, 0.18);
      this.r = rand(1.3, 3.2);
      this.core = Math.random() < 0.22;
      if (this.core) this.r = rand(3.5, 6.5);
      this.pulse = rand(0, Math.PI * 2);
    }
    step() {
      this.x += this.vx; this.y += this.vy;
      if (this.x < 0 || this.x > w) this.vx *= -1;
      if (this.y < 0 || this.y > h) this.vy *= -1;
      this.pulse += 0.02;

      // gentle repulsion from the cursor for a subtle "alive" reaction
      if (mouse.active) {
        const dx = this.x - mouse.x, dy = this.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const radius = 140;
        if (dist < radius && dist > 0.01) {
          const force = (1 - dist / radius) * 0.6;
          this.x += (dx / dist) * force;
          this.y += (dy / dist) * force;
        }
      }
    }
  }

  function populate() {
    const area = w * h;
    const scale = Math.max(0.6, Math.min(1.8, area / (1440 * 900)));
    const count = Math.round(NODE_COUNT_BASE * scale);
    nodes = Array.from({ length: count }, () => new Node());
    blobs = Array.from({ length: 4 }, () => new Blob());
  }
  populate();
  window.addEventListener('resize', populate);

  function draw() {
    ctx.clearRect(0, 0, w, h);

    blobs.forEach(b => { b.step(); b.draw(); });

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const maxDist = 165;
        if (dist < maxDist) {
          const op = (1 - dist / maxDist) * 0.55;
          ctx.strokeStyle = `rgba(120,220,255,${op})`;
          ctx.lineWidth = 0.7;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    nodes.forEach(n => {
      n.step();
      const glow = n.core ? 20 : 9;
      const alpha = n.core ? (0.7 + 0.3 * Math.sin(n.pulse)) : 0.9;
      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * glow * 0.55);
      grad.addColorStop(0, `rgba(160,244,255,${alpha})`);
      grad.addColorStop(1, 'rgba(79,224,255,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r * glow * 0.55, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(235,253,255,${n.core ? 1 : 0.9})`;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }
  draw();
})();