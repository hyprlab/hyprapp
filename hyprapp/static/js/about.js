/* The About section's hero: an animated sine-wave gradient, drawn only while
 * it is on screen and never under reduced motion. */
import { prefersReducedMotion } from "./dom.js";

var W = 200, H = 120;

function hslToRgb(h, s, l) {
  h /= 360;
  var a = s * Math.min(l, 1 - l);
  var f = function (n) {
    var k = (n + h * 12) % 12;
    return Math.round((l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))) * 255);
  };
  return [f(0), f(8), f(4)];
}

function rand(a, b) { return a + Math.random() * (b - a); }

// A triadic palette from a random base hue: every visit looks different and
// none of them clash.
function randomPalette() {
  var hueBase = Math.random() * 360;
  var triad = [0, 120, 240].map(function (d) { return (hueBase + d + rand(-8, 8) + 360) % 360; });
  for (var i = triad.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = triad[i]; triad[i] = triad[j]; triad[j] = tmp;
  }
  return triad.map(function (h) { return hslToRgb(h, 1, 0.55); });
}

function randomWave() {
  var rot;
  var wave = {
    freq1: rand(2.2, 4.0), freq2: rand(5.0, 8.0),
    amp1: rand(0.16, 0.28), amp2: rand(0.06, 0.12),
    speed1: rand(0.05, 0.12) * (Math.random() < 0.5 ? 1 : -1),
    speed2: rand(0.06, 0.14) * (Math.random() < 0.5 ? 1 : -1),
    phase: Math.random() * Math.PI * 2
  };
  rot = Math.random() * Math.PI * 2;
  wave.cosR = Math.cos(rot);
  wave.sinR = Math.sin(rot);
  return wave;
}

function paint(d, rgb, w, t) {
  var n = rgb.length, maxDim = Math.max(W, H);
  var p1 = t * w.speed1, p2 = t * w.speed2 + w.phase;
  for (var y = 0; y < H; y++) {
    for (var x = 0; x < W; x++) {
      var cx = x - W / 2, cy = y - H / 2;
      var rx = cx * w.cosR - cy * w.sinR, ry = cx * w.sinR + cy * w.cosR;
      var nx = (rx + maxDim / 2) / maxDim, ny = (ry + maxDim / 2) / maxDim;
      var wave = Math.sin(nx * w.freq1 + p1) * w.amp1 + Math.sin(nx * w.freq2 + p2) * w.amp2;
      var g = Math.min(0.9999, Math.max(0, ny + wave));
      var seg = g * (n - 1), lo = Math.floor(seg), f = seg - lo;
      var c0 = rgb[lo], c1 = rgb[Math.min(lo + 1, n - 1)];
      var o = (y * W + x) * 4;
      d[o] = c0[0] + (c1[0] - c0[0]) * f;
      d[o + 1] = c0[1] + (c1[1] - c0[1]) * f;
      d[o + 2] = c0[2] + (c1[2] - c0[2]) * f;
      d[o + 3] = 255;
    }
  }
}

function animate(canvas) {
  canvas.width = W; canvas.height = H;
  var cctx = canvas.getContext("2d");
  var rgb = randomPalette();
  var wave = randomWave();
  var img = cctx.createImageData(W, H);
  var running = false, start = 0;

  function frame(now) {
    if (!running) return;
    paint(img.data, rgb, wave, (now - start) / 1000);
    cctx.putImageData(img, 0, 0);
    requestAnimationFrame(frame);
  }
  // Animate only while the canvas is visible (the About section is open).
  new IntersectionObserver(function (entries) {
    var visible = entries[0].isIntersecting;
    if (visible && !running) {
      running = true;
      start = performance.now();
      requestAnimationFrame(frame);
    } else if (!visible) {
      running = false;
    }
  }).observe(canvas);
}

var canvas = document.querySelector(".about-hero-bg");
if (canvas && !prefersReducedMotion() && "IntersectionObserver" in window) animate(canvas);
