import { deflateSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const publicDir = fileURLToPath(new URL("../public/", import.meta.url));
const iconsDir = join(publicDir, "icons");
const screenshotsDir = join(publicDir, "screenshots");
mkdirSync(iconsDir, { recursive: true });
mkdirSync(screenshotsDir, { recursive: true });

function crc32(buffer) {
  let crc = ~0;
  for (const byte of buffer) {
    crc ^= byte;
    for (let i = 0; i < 8; i += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return ~crc >>> 0;
}

function chunk(type, data) {
  const typeBuffer = Buffer.from(type);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([length, typeBuffer, data, crc]);
}

function makePng(width, height, painter) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * (width * 4 + 1);
    raw[row] = 0;
    for (let x = 0; x < width; x += 1) {
      const [r, g, b, a] = painter(x, y, width, height);
      const index = row + 1 + x * 4;
      raw[index] = r;
      raw[index + 1] = g;
      raw[index + 2] = b;
      raw[index + 3] = a;
    }
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

function roundedRectMask(x, y, w, h, radius) {
  const dx = Math.max(radius - x, 0, x - (w - radius - 1));
  const dy = Math.max(radius - y, 0, y - (h - radius - 1));
  return dx * dx + dy * dy <= radius * radius;
}

function iconPainter(maskable = false) {
  return (x, y, w, h) => {
    const pad = maskable ? 0 : Math.round(w * 0.08);
    const inside = roundedRectMask(x - pad, y - pad, w - pad * 2, h - pad * 2, Math.round(w * 0.18));
    if (!inside) return [0, 0, 0, 0];
    const center = w / 2;
    const dist = Math.hypot(x - center, y - h * 0.45) / center;
    const glow = Math.max(0, 1 - dist);
    const ember = Math.round(30 + glow * 82);
    const base = 11 + Math.round(glow * 8);
    const inC = x > w * 0.27 && x < w * 0.45 && y > h * 0.30 && y < h * 0.70;
    const inFTop = x > w * 0.48 && x < w * 0.74 && y > h * 0.31 && y < h * 0.42;
    const inFMid = x > w * 0.48 && x < w * 0.67 && y > h * 0.48 && y < h * 0.58;
    const letter = inC || inFTop || inFMid;
    const dot = Math.hypot(x - w * 0.77, y - h * 0.65) < w * 0.055;
    if (letter) return [244, 241, 234, 255];
    if (dot) return [224, 83, 61, 255];
    return [base + ember, base + 8, base + 10, 255];
  };
}

function screenshotPainter(wide = false) {
  return (x, y, w, h) => {
    const bg = [11, 11, 14, 255];
    const surface = [19, 19, 24, 255];
    const rule = [37, 37, 46, 255];
    const ember = [224, 83, 61, 255];
    const paper = [244, 241, 234, 255];
    const sidebar = wide ? x < w * 0.22 : y < h * 0.12;
    if (sidebar) return x % 31 < 2 || y % 29 < 2 ? rule : [8, 8, 10, 255];
    const card1 = x > w * 0.28 && x < w * 0.54 && y > h * 0.24 && y < h * 0.55;
    const card2 = x > w * 0.58 && x < w * 0.88 && y > h * 0.24 && y < h * 0.55;
    const mobileCard = !wide && x > w * 0.08 && x < w * 0.92 && y > h * 0.28 && y < h * 0.50;
    if (card1 || card2 || mobileCard) return surface;
    if (y > h * 0.17 && y < h * 0.19 && x > w * 0.28) return ember;
    if (x > w * 0.30 && x < w * 0.70 && y > h * 0.10 && y < h * 0.13) return paper;
    return bg;
  };
}

writeFileSync(join(iconsDir, "icon-192.png"), makePng(192, 192, iconPainter(false)));
writeFileSync(join(iconsDir, "icon-512.png"), makePng(512, 512, iconPainter(false)));
writeFileSync(join(iconsDir, "icon-512-maskable.png"), makePng(512, 512, iconPainter(true)));
writeFileSync(join(iconsDir, "apple-touch-icon.png"), makePng(180, 180, iconPainter(false)));
writeFileSync(join(screenshotsDir, "pwa-mobile.png"), makePng(750, 1334, screenshotPainter(false)));
writeFileSync(join(screenshotsDir, "pwa-wide.png"), makePng(1280, 720, screenshotPainter(true)));

console.log("PWA assets generated");
