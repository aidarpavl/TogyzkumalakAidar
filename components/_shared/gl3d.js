  // ================= GL3D: шағын WebGL қозғалтқышы + ат пен шабандоздың 3D үлгілері =================
  const G3 = (function () {
    // ---- геометрия (деректер; әр WebGL контекстке жеке жүктеледі)
    function sphereD(W, H) {
      const P = [], N = [], I = [];
      for (let y = 0; y <= H; y++) { const v = y / H * Math.PI;
        for (let x = 0; x <= W; x++) { const u = x / W * Math.PI * 2;
          const px = Math.sin(v) * Math.cos(u), py = Math.cos(v), pz = Math.sin(v) * Math.sin(u);
          P.push(px, py, pz); N.push(px, py, pz); } }
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const a = y * (W + 1) + x, b = a + W + 1; I.push(a, b, a + 1, b, b + 1, a + 1); }
      return [P, N, I];
    }
    function cylD(S, r0, r1) {
      const P = [], N = [], I = [];
      for (let i = 0; i <= S; i++) { const a = i / S * Math.PI * 2, c = Math.cos(a), s = Math.sin(a), ny = (r0 - r1), l = Math.hypot(1, ny);
        P.push(c * r0, -0.5, s * r0, c * r1, 0.5, s * r1); N.push(c / l, ny / l, s / l, c / l, ny / l, s / l); }
      for (let i = 0; i < S; i++) { const a = i * 2; I.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
      const base = P.length / 3;
      P.push(0, 0.5, 0); N.push(0, 1, 0); P.push(0, -0.5, 0); N.push(0, -1, 0);
      for (let i = 0; i <= S; i++) { const a = i / S * Math.PI * 2; P.push(Math.cos(a) * r1, 0.5, Math.sin(a) * r1); N.push(0, 1, 0); P.push(Math.cos(a) * r0, -0.5, Math.sin(a) * r0); N.push(0, -1, 0); }
      for (let i = 0; i < S; i++) { const a = base + 2 + i * 2; I.push(base, a + 2, a, base + 1, a + 1, a + 3); }
      return [P, N, I];
    }
    function boxD() {
      const P = [], N = [], I = [];
      [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]].forEach((n) => {
        const u = n[0] ? [0, 1, 0] : [1, 0, 0], v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]], b = P.length / 3;
        [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(([a, c]) => { P.push((n[0] + u[0] * a + v[0] * c) / 2, (n[1] + u[1] * a + v[1] * c) / 2, (n[2] + u[2] * a + v[2] * c) / 2); N.push(...n); });
        I.push(b, b + 1, b + 2, b, b + 2, b + 3); });
      return [P, N, I];
    }
    const GEO = { SPH: sphereD(28, 18), CYL: cylD(18, 1, 1), CONE: cylD(14, 1, 0.02), TAPER: cylD(16, 1, 0.72), BOX: boxD() };

    // ---- матрицалар
    const I4 = () => new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
    function mul(a, b) { const o = new Float32Array(16);
      for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let s = 0; for (let k = 0; k < 4; k++) s += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = s; } return o; }
    const T = (x, y, z) => { const m = I4(); m[12] = x; m[13] = y; m[14] = z; return m; };
    const Sc = (x, y, z) => { const m = I4(); m[0] = x; m[5] = y; m[10] = z; return m; };
    const RX = (a) => { const m = I4(), c = Math.cos(a), s = Math.sin(a); m[5] = c; m[6] = s; m[9] = -s; m[10] = c; return m; };
    const RY = (a) => { const m = I4(), c = Math.cos(a), s = Math.sin(a); m[0] = c; m[2] = -s; m[8] = s; m[10] = c; return m; };
    const RZ = (a) => { const m = I4(), c = Math.cos(a), s = Math.sin(a); m[0] = c; m[1] = s; m[4] = -s; m[5] = c; return m; };
    function persp(f, a, n, fa) { const t = 1 / Math.tan(f / 2), m = new Float32Array(16);
      m[0] = t / a; m[5] = t; m[10] = (fa + n) / (n - fa); m[11] = -1; m[14] = 2 * fa * n / (n - fa); return m; }
    function look(e, t, u) {
      let z = [e[0] - t[0], e[1] - t[1], e[2] - t[2]]; let l = Math.hypot(...z); z = z.map((v) => v / l);
      let x = [u[1] * z[2] - u[2] * z[1], u[2] * z[0] - u[0] * z[2], u[0] * z[1] - u[1] * z[0]]; l = Math.hypot(...x); x = x.map((v) => v / l);
      const y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]];
      return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0,
        -(x[0] * e[0] + x[1] * e[1] + x[2] * e[2]), -(y[0] * e[0] + y[1] * e[1] + y[2] * e[2]), -(z[0] * e[0] + z[1] * e[1] + z[2] * e[2]), 1]);
    }
    function alignY(d) {
      const l = Math.hypot(...d), v = d.map((x) => x / l), s = Math.hypot(v[2], v[0]), c = v[1];
      if (s < 1e-6) return c > 0 ? I4() : RX(Math.PI);
      const k = [v[2] / s, 0, -v[0] / s], t = 1 - c, m = I4();
      const K = [[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]];
      for (let r = 0; r < 3; r++) for (let cc = 0; cc < 3; cc++) m[cc * 4 + r] = (r === cc ? c : 0) + s * K[r][cc] + t * k[r] * k[cc];
      return m;
    }

    // ---- сахнаны бір рет жазу, барлық камерада салу
    let REC = [];
    function draw(key, M, col, spec, alpha) { REC.push([key, M, col, spec, alpha]); }
    function P(m, key, t, r, s, col, spec, alpha) {
      let M = mul(m, T(t[0], t[1], t[2]));
      if (r) { if (r[2]) M = mul(M, RZ(r[2])); if (r[1]) M = mul(M, RY(r[1])); if (r[0]) M = mul(M, RX(r[0])); }
      draw(key, mul(M, Sc(s[0], s[1], s[2])), col, spec, alpha);
    }
    function seg(m, a, b, r0, col, key, spec) {
      const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], l = Math.hypot(...d);
      let M = mul(m, T((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)); M = mul(M, alignY(d));
      if (key === "SPH") draw(key, mul(M, Sc(r0, l * 0.95, r0)), col, spec);
      else draw(key || "CYL", mul(M, Sc(r0, l, r0)), col, spec);
    }
    function record(fn) { REC = []; fn(); const r = REC; REC = []; return r; }

    const VS = `attribute vec3 p; attribute vec3 n; attribute vec4 m0; attribute vec4 m1; attribute vec4 m2; attribute vec4 m3; attribute vec4 ic; attribute float ia;
      uniform mat4 VP; varying vec3 vN; varying vec3 vW; varying vec4 vC; varying float vA;
      void main(){ mat4 M = mat4(m0, m1, m2, m3); vec4 w = M * vec4(p, 1.0); vW = w.xyz; vN = mat3(M) * n; vC = ic; vA = ia; gl_Position = VP * w; }`;
    const FS = `precision mediump float; varying vec3 vN; varying vec3 vW; varying vec4 vC; varying float vA;
      uniform vec3 L; uniform vec3 E; uniform vec3 F; uniform vec2 FR;
      void main(){
        vec3 n = normalize(vN); if (!gl_FrontFacing) n = -n;
        float d = max(dot(n, L), 0.0); float h = 0.5 + 0.5 * n.y;
        vec3 amb = mix(vec3(0.40, 0.33, 0.24), vec3(0.60, 0.68, 0.80), h) * 0.62;
        vec3 v = normalize(E - vW); vec3 r = reflect(-L, n);
        float sp = pow(max(dot(r, v), 0.0), 20.0) * vC.a;
        float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0) * 0.09;
        vec3 col = vC.rgb * (amb + d * vec3(1.0, 0.95, 0.86) * 0.82) + sp + rim * vec3(1.0, 0.95, 0.85);
        float f = clamp((length(E - vW) - FR.x) / (FR.y - FR.x), 0.0, 1.0);
        gl_FragColor = vec4(mix(col, F, f * f), vA);
      }`;

    // ---- бір камера = бір WebGL кенеп
    function makeView(cv, bw, bh) {
      let gl = null;
      try { gl = cv.getContext("webgl", { antialias: true, alpha: true, premultipliedAlpha: false }); } catch (e) { gl = null; }
      if (!gl) return null;
      const EXT = gl.getExtension("ANGLE_instanced_arrays");
      if (!EXT) return null;
      const sh = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); return s; };
      const pr = gl.createProgram();
      gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
      if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) return null;
      gl.useProgram(pr);
      const U = {}; ["VP", "L", "E", "F", "FR"].forEach((k) => U[k] = gl.getUniformLocation(pr, k));
      const A = {}; ["p", "n", "m0", "m1", "m2", "m3", "ic", "ia"].forEach((k) => A[k] = gl.getAttribLocation(pr, k));
      const meshes = {};
      Object.entries(GEO).forEach(([key, [Pp, Nn, Ii]]) => {
        const b = (d, t) => { const x = gl.createBuffer(); gl.bindBuffer(t, x); gl.bufferData(t, d, gl.STATIC_DRAW); return x; };
        meshes[key] = { p: b(new Float32Array(Pp), gl.ARRAY_BUFFER), n: b(new Float32Array(Nn), gl.ARRAY_BUFFER), i: b(new Uint16Array(Ii), gl.ELEMENT_ARRAY_BUFFER), c: Ii.length };
      });
      const ibuf = gl.createBuffer();
      gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      let VPm = I4(), w = bw, h = bh, q = 1;
      const view = {
        setQuality(nq) { q = nq; cv.width = Math.round(bw * q); cv.height = Math.round(bh * q); },
        camera(eye, target, fov, fog) {
          VPm = mul(persp(fov || 0.7, bw / bh, 0.1, 400), look(eye, target, [0, 1, 0]));
          gl.viewport(0, 0, cv.width, cv.height);
          gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
          const L = [0.45, 0.8, 0.35], ll = Math.hypot(...L);
          gl.uniformMatrix4fv(U.VP, false, VPm); gl.uniform3fv(U.L, L.map((v) => v / ll)); gl.uniform3fv(U.E, eye);
          gl.uniform3fv(U.F, fog || [0.84, 0.9, 0.93]); gl.uniform2fv(U.FR, [25, 170]);
        },
        project(p) {
          const V = VPm, x = V[0] * p[0] + V[4] * p[1] + V[8] * p[2] + V[12], y = V[1] * p[0] + V[5] * p[1] + V[9] * p[2] + V[13];
          const ww = V[3] * p[0] + V[7] * p[1] + V[11] * p[2] + V[15];
          if (ww <= 0.01) return null; return [(x / ww * 0.5 + 0.5) * bw, (1 - (y / ww * 0.5 + 0.5)) * bh];
        },
        draw(list) {
          const batch = (key, items) => {
            const msh = meshes[key], n = items.length, data = new Float32Array(n * 21);
            for (let i = 0; i < n; i++) { const d = items[i], o = i * 21; data.set(d[1], o);
              data[o + 16] = d[2][0]; data[o + 17] = d[2][1]; data[o + 18] = d[2][2]; data[o + 19] = d[3] || 0.06; data[o + 20] = d[4] == null ? 1 : d[4]; }
            gl.bindBuffer(gl.ARRAY_BUFFER, ibuf); gl.bufferData(gl.ARRAY_BUFFER, data, gl.STREAM_DRAW);
            const st = 84;
            ["m0", "m1", "m2", "m3"].forEach((k, j) => { gl.enableVertexAttribArray(A[k]); gl.vertexAttribPointer(A[k], 4, gl.FLOAT, false, st, j * 16); EXT.vertexAttribDivisorANGLE(A[k], 1); });
            gl.enableVertexAttribArray(A.ic); gl.vertexAttribPointer(A.ic, 4, gl.FLOAT, false, st, 64); EXT.vertexAttribDivisorANGLE(A.ic, 1);
            gl.enableVertexAttribArray(A.ia); gl.vertexAttribPointer(A.ia, 1, gl.FLOAT, false, st, 80); EXT.vertexAttribDivisorANGLE(A.ia, 1);
            gl.bindBuffer(gl.ARRAY_BUFFER, msh.p); gl.enableVertexAttribArray(A.p); gl.vertexAttribPointer(A.p, 3, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, msh.n); gl.enableVertexAttribArray(A.n); gl.vertexAttribPointer(A.n, 3, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, msh.i);
            EXT.drawElementsInstancedANGLE(gl.TRIANGLES, msh.c, gl.UNSIGNED_SHORT, 0, n);
          };
          const groups = {}, alpha = {};
          for (const d of list) { const tgt = (d[4] != null && d[4] < 1) ? alpha : groups; (tgt[d[0]] = tgt[d[0]] || []).push(d); }
          Object.keys(groups).forEach((k) => batch(k, groups[k]));
          gl.depthMask(false); Object.keys(alpha).forEach((k) => batch(k, alpha[k])); gl.depthMask(true);
        },
      };
      return view;
    }
    return { SPH: "SPH", CYL: "CYL", CONE: "CONE", TAPER: "TAPER", BOX: "BOX", I4, mul, T, Sc, RX, RY, RZ, P, seg, record, makeView };
  })();

  const hex = (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];

  // ---- 3D ат: m — аттың түбі (жерде), +x алға қарайды
  function horse3d(m, k, ph, opts) {
    const { P, seg, SPH, CYL, CONE, TAPER, BOX, mul, T, RZ } = G3;
    const c0 = hex(k.horse[0]), c1 = hex(k.horse[1]), c2 = hex(k.horse[2]), mane = hex(k.mane), hoof = hex(k.hoof);
    const bob = Math.sin(ph * 2) * 0.06, pitch = Math.sin(ph * 2 + 0.6) * 0.05;
    const mb = mul(mul(m, T(0, bob, 0)), RZ(pitch));
    // көлеңке
    P(m, SPH, [0, 0.02, 0], null, [1.25, 0.01, 0.45], [0.18, 0.15, 0.08], 0, 0.35);
    // дене
    P(mb, SPH, [0, 1.26, 0], null, [0.9, 0.37, 0.33], c0, 0.08);
    P(mb, SPH, [-0.6, 1.3, 0], [0, 0, 0.1], [0.46, 0.41, 0.35], c0, 0.08);
    P(mb, SPH, [0.6, 1.25, 0], [0, 0, -0.2], [0.42, 0.44, 0.32], c0, 0.08);
    P(mb, SPH, [0.0, 1.08, 0], null, [0.72, 0.2, 0.28], c1, 0.04);
    [-1, 1].forEach((sd) => {   // иық пен сан бұлшықеттері
      P(mb, SPH, [0.52, 1.16, sd * 0.15], [0, 0, -0.35], [0.3, 0.36, 0.18], c0, 0.08);
      P(mb, SPH, [-0.62, 1.18, sd * 0.15], [0, 0, 0.25], [0.36, 0.4, 0.2], c0, 0.08); });
    // мойын мен бас
    const nk = Math.sin(ph * 2) * 0.06;
    P(mb, SPH, [0.8, 1.48, 0], [0, 0, 0.7], [0.36, 0.3, 0.22], c0, 0.08);
    P(mb, SPH, [1.0, 1.68, 0], [0, 0, 0.95 + nk], [0.5, 0.25, 0.18], c0, 0.08);
    const mh = mul(mul(mb, T(1.3, 2.02 + nk * 0.3, 0)), RZ(-1.05 + nk));
    P(mh, SPH, [0.2, 0, 0], null, [0.33, 0.15, 0.13], c0, 0.12);
    P(mh, SPH, [0.47, -0.02, 0], null, [0.14, 0.12, 0.11], c1, 0.08);
    if (k.blaze) P(mh, SPH, [0.28, 0.1, 0], null, [0.24, 0.06, 0.05], hex(k.blaze), 0.05);
    [-1, 1].forEach((sd) => {
      P(mh, CONE, [-0.02, 0.17, sd * 0.06], [sd * 0.15, 0, 0.35], [0.045, 0.14, 0.04], c1);
      P(mh, SPH, [0.13, 0.07, sd * 0.11], null, [0.03, 0.03, 0.02], [0.05, 0.04, 0.03], 0.6);
      P(mh, SPH, [0.56, -0.02, sd * 0.06], null, [0.02, 0.02, 0.02], [0.1, 0.07, 0.05]);
      // жүген
      P(mh, BOX, [0.3, 0.0, sd * 0.135], [0, 0, 0.1], [0.42, 0.025, 0.01], [0.35, 0.1, 0.07]);
      P(mh, SPH, [0.3, 0.0, sd * 0.14], null, [0.022, 0.022, 0.01], hex(k.trim), 0.9);
    });
    // жал
    for (let i = 0; i < 8; i++) { const t = i / 7;
      P(mb, BOX, [0.74 + t * 0.52, 1.62 + t * 0.44 + 0.1, 0], [0, 0, 0.85 + Math.sin(ph * 2 + i) * 0.08], [0.09, 0.17, 0.05], mane); }
    // құйрық
    let tp = [-1.02, 1.48, 0];
    for (let i = 0; i < 7; i++) { const a = -0.55 - i * 0.16 + Math.sin(ph * 2 + i * 0.6) * 0.14;
      const np = [tp[0] - 0.12 * Math.cos(a) - 0.05, tp[1] + 0.12 * Math.sin(a), Math.sin(ph + i * 0.8) * 0.05];
      seg(mb, tp, np, 0.1 - i * 0.006, mane, SPH); tp = np; }
    // аяқтар (галоп)
    const leg = (hip, a1, a2, l1, l2, r1, r2, col) => {
      const m1 = mul(mul(mb, T(hip[0], hip[1], hip[2])), RZ(a1));
      P(m1, SPH, [0, -0.04, 0], null, [r1 * 1.25, r1 * 1.5, r1 * 1.15], col, 0.06);
      P(m1, SPH, [0, -l1 / 2 + 0.02, 0], null, [r1, l1 / 2 + 0.06, r1 * 0.85], col, 0.06);
      const m2 = mul(mul(m1, T(0, -l1, 0)), RZ(a2));
      P(m2, SPH, [0, 0, 0], null, [r2 * 1.1, r2 * 1.1, r2 * 1.1], col);
      P(m2, CYL, [0, -l2 / 2, 0], null, [r2, l2, r2], col, 0.08);
      P(m2, SPH, [0, -l2, 0], null, [r2 * 1.15, r2, r2 * 1.15], col);
      P(m2, CYL, [0.02, -l2 - 0.07, 0], null, [r2 * 1.35, 0.1, r2 * 1.35], hoof, 0.2);
    };
    [[1, 0, c2, -0.18], [-1, 0.9, c1, 0.18]].forEach(([sd, o, col, z]) => {
      const hp = ph + o, fp = ph + 2.2 + o;
      leg([-0.66, 1.18, z], 0.12 + 0.5 * Math.sin(hp), -(0.45 + 0.5 * Math.max(0, Math.sin(hp + 1.4))), 0.56, 0.58, 0.15, 0.062, col);
      leg([0.6, 1.08, z], 0.05 + 0.6 * Math.sin(fp), -(0.1 + 1.1 * Math.max(0, Math.sin(fp + 1.6))), 0.5, 0.56, 0.125, 0.058, col);
    });
    // тоқым, ер
    const tk = hex(k.tokym), tr = hex(k.trim);
    P(mb, BOX, [0, 1.63, 0], null, [0.66, 0.04, 0.74], tk);
    [-1, 1].forEach((sd) => { P(mb, BOX, [0, 1.42, sd * 0.37], [sd * 0.08, 0, 0], [0.62, 0.42, 0.025], tk);
      P(mb, BOX, [0, 1.21, sd * 0.385], [sd * 0.08, 0, 0], [0.64, 0.05, 0.03], tr, 0.6);
      for (let i = 0; i < 5; i++) P(mb, SPH, [-0.24 + i * 0.12, 1.32, sd * 0.392], null, [0.025, 0.025, 0.01], tr, 0.8); });
    P(mb, BOX, [0, 1.7, 0], null, [0.46, 0.1, 0.44], [0.33, 0.17, 0.07], 0.2);
    P(mb, SPH, [0.22, 1.77, 0], null, [0.06, 0.07, 0.06], tr, 0.8);
    return mb;
  }

  // ---- 3D шабандоз: m — ердің үстіндегі нүкте. role: girl | jigit | jigit2
  function rider3d(mh, k, role, ph, lean, leanSide, whipUp) {
    const { P, seg, SPH, CYL, CONE, TAPER, BOX, mul, T, RX, RZ } = G3;
    const coat = hex(role === "girl" ? k.robe : k.robe), dress = hex(k.dress), skin = hex(k.skin), hair = hex(k.hair),
      trim = hex(k.trim), boot = [0.1, 0.07, 0.05], robe2 = hex(k.robe2);
    const bounce = Math.sin(ph * 2 + 0.4) * 0.03;
    const mr = mul(mul(mh, T(0.02, 1.76 + bounce, 0)), RX((lean || 0) * (leanSide || 0) * 0.95));
    // аяқтар
    [-1, 1].forEach((sd) => {
      const hip = [0, 0, sd * 0.13], knee = [0.3, -0.16, sd * 0.36], ank = [0.2, -0.56, sd * 0.38];
      seg(mr, hip, knee, 0.095, role === "girl" ? dress : robe2);
      seg(mr, knee, ank, 0.065, boot); P(mr, BOX, [ank[0] + 0.06, ank[1] - 0.03, ank[2]], null, [0.2, 0.07, 0.08], boot);
      P(mr, CYL, [ank[0] + 0.04, ank[1] - 0.05, ank[2]], [0, 0, 0], [0.07, 0.015, 0.07], trim, 0.8);
    });
    // етек / шапан
    const sw = Math.sin(ph * 1.7) * 0.12;
    if (role === "girl") P(mr, CONE, [-0.08, -0.08, 0], [0, 0, 0.45 + sw * 0.5], [0.34, 0.42, 0.36], dress, 0.05);
    else P(mr, CONE, [-0.1, -0.05, 0], [0, 0, 0.55 + sw * 0.5], [0.3, 0.38, 0.33], robe2, 0.05);
    // дене (алға еңкейген)
    const mt = mul(mr, RZ(-0.38));
    P(mt, SPH, [0, 0.3, 0], null, [0.19, 0.33, 0.22], role === "girl" ? dress : coat, 0.06);
    P(mt, SPH, [0, 0.5, 0], null, [0.16, 0.12, 0.25], role === "girl" ? dress : coat, 0.06);
    if (role === "girl") {
      P(mt, SPH, [0.005, 0.3, 0], null, [0.195, 0.31, 0.225], coat, 0.18);           // барқыт камзол
      for (let i = 0; i < 4; i++) P(mt, SPH, [0.17, 0.12 + i * 0.1, 0], null, [0.018, 0.018, 0.018], trim, 0.9);
      P(mt, BOX, [0.16, 0.3, 0], [0, 0, 0.05], [0.01, 0.5, 0.02], trim, 0.7);
    } else {
      P(mt, CYL, [0, 0.12, 0], null, [0.185, 0.06, 0.215], trim, 0.7);               // белбеу
      P(mt, BOX, [0.165, 0.52, 0], null, [0.02, 0.12, 0.08], dress);                  // жаға
    }
    // қолдар: тізгінге
    const sh = (sd) => [0.0, 0.55, sd * 0.23];
    [-1, 1].forEach((sd) => {
      const up = role !== "girl" && sd === 1 && whipUp && !lean;
      const reach = lean && sd === leanSide;
      let el, hd;
      if (reach) { el = [0.22, 0.2, sd * 0.38]; hd = [0.28, -0.32, sd * 0.5]; }
      else if (up) { el = [0.02, 0.84, 0.3]; hd = [0.1, 1.08, 0.32]; }
      else { el = [0.22, 0.35, sd * 0.25]; hd = [0.46, 0.18, sd * 0.12]; }
      seg(mt, sh(sd), el, 0.072, role === "girl" ? dress : coat);
      P(mt, SPH, el, null, [0.068, 0.068, 0.068], role === "girl" ? dress : coat);
      seg(mt, el, hd, 0.06, role === "girl" ? dress : coat);
      P(mt, SPH, hd, null, [0.045, 0.045, 0.045], skin);
      if (up) { const wa = Math.sin(ph * 2) * 0.3;
        seg(mt, hd, [-0.15, 1.35, 0.36], 0.012, [0.3, 0.17, 0.07]);
        seg(mt, [-0.15, 1.35, 0.36], [-0.45 + wa * 0.3, 1.25 + wa * 0.4, 0.38], 0.006, [0.25, 0.14, 0.06]); }
    });
    // бас
    P(mt, CYL, [0, 0.64, 0], null, [0.05, 0.08, 0.05], skin);
    P(mt, SPH, [0.02, 0.78, 0], null, [0.115, 0.13, 0.11], skin, 0.08);
    P(mt, SPH, [0.115, 0.79, 0.04], null, [0.012, 0.012, 0.012], [0.05, 0.04, 0.03]);
    P(mt, SPH, [0.115, 0.79, -0.04], null, [0.012, 0.012, 0.012], [0.05, 0.04, 0.03]);
    P(mt, SPH, [0.122, 0.75, 0], null, [0.018, 0.022, 0.016], skin);
    if (role === "girl") {
      P(mt, SPH, [-0.01, 0.8, 0], null, [0.108, 0.1, 0.105], hair);                   // шаш
      P(mt, CYL, [0.0, 0.86, 0], null, [0.125, 0.045, 0.125], [0.97, 0.95, 0.9], 0.05); // үкілі бөріктің жиегі
      P(mt, CYL, [0.0, 0.94, 0], null, [0.1, 0.13, 0.1], coat, 0.3);
      P(mt, SPH, [0.0, 1.01, 0], null, [0.1, 0.03, 0.1], coat, 0.3);
      P(mt, SPH, [0.0, 1.03, 0], null, [0.022, 0.022, 0.022], trim, 0.9);
      for (let f = -1; f <= 1; f++) seg(mt, [0, 1.03, 0], [-0.12 + f * 0.02, 1.25 + Math.sin(ph + f) * 0.02, f * 0.06], 0.012, [0.98, 0.97, 0.94], CONE);
      [-1, 1].forEach((sd) => { let p0 = [-0.08, 0.76, sd * 0.06];          // бұрымдар
        for (let i = 0; i < 6; i++) { const p1 = [p0[0] - 0.07 - i * 0.01, p0[1] - 0.06 + Math.sin(ph * 2 + i + sd) * 0.015, p0[2] + sd * 0.008];
          seg(mt, p0, p1, 0.025 - i * 0.002, hair); p0 = p1; }
        P(mt, SPH, p0, null, [0.022, 0.022, 0.022], trim, 0.9); });
      P(mt, SPH, [0.02, 0.7, 0.1], null, [0.012, 0.012, 0.012], trim, 0.9);
    } else {
      P(mt, BOX, [0.12, 0.72, 0], null, [0.01, 0.012, 0.08], hair);                   // мұрт
      P(mt, SPH, [0.0, 0.88, 0], null, [0.14, 0.09, 0.14], hex(k.fur), 0.02);        // тымақ
      P(mt, CYL, [0.0, 0.95, 0], null, [0.09, 0.08, 0.09], hex(k.hat), 0.2);
      P(mt, SPH, [0.0, 1.0, 0], null, [0.025, 0.025, 0.025], trim, 0.9);
      [-1, 1].forEach((sd) => P(mt, BOX, [-0.03, 0.78, sd * 0.12], [sd * 0.2, 0, 0], [0.08, 0.14, 0.03], hex(k.fur), 0.02));
      P(mt, BOX, [-0.11, 0.8, 0], [0, 0, -0.25], [0.04, 0.16, 0.18], hex(k.fur), 0.02);
    }
    // тізгін
    [-1, 1].forEach((sd) => seg(mh, [0.62, 1.95 + bounce, sd * 0.1], [1.42, 1.8, sd * 0.12], 0.008, [0.2, 0.1, 0.05]));
  }

  // ---- ортақ көрініс бөлшектері
  function ground3d(cx, opts) {
    const { P, CYL, CONE, BOX, I4 } = G3, m = I4();
    P(m, BOX, [cx, -0.05, 0], null, [420, 0.1, 160], [0.72, 0.68, 0.36]);
    P(m, BOX, [cx, 0.005, 0], null, [420, 0.01, opts.trackW || 4.2], [0.6, 0.5, 0.32]);
    // шөп шоқтары
    const base = Math.floor(cx / 6) * 6;
    for (let x = base - 48; x < base + 90; x += 9) for (let j = 0; j < 3; j++) {
      const r = Math.sin(x * 12.9898 + j * 78.233) * 43758.5453, f = r - Math.floor(r);
      const z = (j === 0 ? -1 : 1) * (3 + f * 20), xx = x + f * 7;
      P(m, CONE, [xx, 0.18, z], null, [0.18 + f * 0.1, 0.36, 0.18], [0.45 + f * 0.1, 0.5, 0.2]);
    }
  }
  function post3d(x, z, col) { const { P, CYL, I4 } = G3; P(I4(), CYL, [x, 0.5, z], null, [0.05, 1.0, 0.05], col || [0.96, 0.96, 0.94], 0.2); }
  function flag3d(x, z) { const { P, CYL, BOX, SPH, I4 } = G3, m = I4();
    P(m, CYL, [x, 1.6, z], null, [0.06, 3.2, 0.06], [0.42, 0.27, 0.14]);
    P(m, BOX, [x + 0.55, 2.8, z], null, [1.0, 0.6, 0.03], [0.96, 0.69, 0.25], 0.2);
    P(m, SPH, [x, 3.25, z], null, [0.1, 0.1, 0.1], [0.9, 0.75, 0.2], 0.9); }
  function sky2d(ctx, w, h, hy, scroll) {
    const g = ctx.createLinearGradient(0, 0, 0, Math.max(10, hy));
    g.addColorStop(0, "#4f9fe3"); g.addColorStop(1, "#d6ecf7");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#8193ab"; ctx.beginPath(); ctx.moveTo(0, hy);
    for (let x = 0; x <= w; x += 24) ctx.lineTo(x, hy - 18 * Math.abs(Math.sin((x + scroll) / 70)) - 10 * Math.abs(Math.sin((x + scroll) / 23)) - 4);
    ctx.lineTo(w, hy + 1); ctx.lineTo(0, hy + 1); ctx.fill();
    ctx.fillStyle = "#d6e6e8"; ctx.fillRect(0, hy, w, h - hy);
  }
  // Бейімделгіш сапа: баяу құрылғыда ажыратымдылықты төмендетеді
  const PERF = { t: 0, n: 0, q: 1 };
  function perfTick(ms, views) {
    PERF.t += ms; PERF.n += 1;
    if (PERF.n >= 20) { const avg = PERF.t / PERF.n; PERF.t = 0; PERF.n = 0;
      let q = PERF.q; if (avg > 40 && q > 0.5) q = Math.max(0.5, q - 0.25); else if (avg < 14 && q < 1) q = Math.min(1, q + 0.25);
      if (q !== PERF.q) { PERF.q = q; views.forEach((v) => v.setQuality(q)); } }
  }
  function view3d(ctx, view, w, h, eye, target, fov, list, scroll) {
    view.camera(eye, target, fov, [0.84, 0.9, 0.93]);
    const dx = target[0] - eye[0], dz = target[2] - eye[2], l = Math.hypot(dx, dz) || 1;
    const hp = view.project([eye[0] + dx / l * 2000, 0, eye[2] + dz / l * 2000]);
    sky2d(ctx, w, h, hp ? Math.max(0, Math.min(h, hp[1])) : h * 0.45, scroll || 0);
    view.draw(list);
  }
  function label3d(ctx, view, p, txt) { const q = view.project(p); if (q && q[0] > -30 && q[0] < 640) {
    ctx.font = "bold 12px system-ui"; ctx.fillStyle = "#fff"; ctx.strokeStyle = "rgba(0,0,0,.55)"; ctx.lineWidth = 3;
    ctx.strokeText(txt, q[0] + 4, q[1]); ctx.fillText(txt, q[0] + 4, q[1]); } }
  // 3D камералары: әр көрініске жеке WebGL кенеп (2D кенептің үстінде)
  function setup3d() {
    const mk = (id, w, h) => { const host = document.getElementById(id).parentElement, c = document.createElement("canvas");
      c.width = w; c.height = h; c.className = "gl3d"; host.insertBefore(c, host.children[1]); return c; };
    const gs = mk("cs", 600, 300), gf = mk("cf", 360, 300), gr = mk("cr", 360, 300);
    const lab = document.createElement("canvas"); lab.width = 600; lab.height = 300; lab.className = "gl3d"; gs.after(lab);
    const V = { s: G3.makeView(gs, 600, 300), f: G3.makeView(gf, 360, 300), r: G3.makeView(gr, 360, 300), lab: lab.getContext("2d") };
    if (!V.s || !V.f || !V.r) { [gs, gf, gr, lab].forEach((c) => c.remove()); return null; }
    return V;
  }
  // ================= GL3D соңы =================
