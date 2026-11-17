  // ================= KURES: балуанның 3D денесі (қаңқа + IK) =================
  const HB = (function () {
    const S = 1.1;                                        // балуандар сәл ірі (≈ 1,95 м)
    const xf = (m, p) => [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12], m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13], m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]];
    const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
    const mulv = (a, k) => [a[0] * k, a[1] * k, a[2] * k], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const len = (a) => Math.sqrt(dot(a, a)), norm = (a) => { const l = len(a) || 1; return mulv(a, 1 / l); };
    const lerp = (a, b, k) => a + (b - a) * k;
    const lerpV = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
    const hex = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255]; };

    // екі буынды IK: a — түбі, c — мақсат, pole — буын бүгілетін бағыт
    function ik(a, c, l1, l2, pole) {
      let d = sub(c, a), dl = len(d);
      const mx = (l1 + l2) * 0.999; if (dl > mx) { d = mulv(d, mx / dl); dl = mx; c = add(a, d); }
      if (dl < 1e-4) dl = 1e-4;
      const dir = mulv(d, 1 / dl), x = (l1 * l1 - l2 * l2 + dl * dl) / (2 * dl), h = Math.sqrt(Math.max(0, l1 * l1 - x * x));
      let pv = sub(pole, a); pv = sub(pv, mulv(dir, dot(pv, dir))); pv = norm(pv);
      return [add(add(a, mulv(dir, x)), mulv(pv, h)), c];
    }

    function blend(a, b, k) {
      const o = {};
      for (const key in a) {
        const va = a[key], vb = b[key] === undefined ? va : b[key];
        if (typeof va === "number") o[key] = lerp(va, vb, k);
        else if (Array.isArray(va) && Array.isArray(va[0])) o[key] = va.map((v, i) => lerpV(v, vb[i], k));
        else if (Array.isArray(va)) o[key] = lerpV(va, vb, k);
        else o[key] = k < 0.5 ? va : vb;
      }
      return o;
    }

    // тұрыс (түбір — табан ортасы, алға +x, жоғары +y, сол жақ +z)
    const BASEPOSE = { hip: [0, 0.88, 0], pel: 0.08, pitch: 0.3, roll: 0, yaw: 0, hp: -0.25, hy: 0, hr: 0,
      feet: [[-0.04, 0.08, 0.2], [0.1, 0.08, -0.2]], hands: [[0.36, 1.02, 0.2], [0.36, 1.02, -0.2]], toe: [0, 0] };

    // қаңқаны есептеу (дүниедегі нүктелер)
    function skeleton(M0, ps) {
      const { mul, T, RX, RY, RZ, Sc } = G3;
      const M = mul(M0, Sc(S, S, S));
      const Mp = mul(mul(M, T(ps.hip[0], ps.hip[1], ps.hip[2])), RZ(-ps.pel));
      const Mc = mul(mul(mul(mul(Mp, T(0, 0.1, 0)), RY(ps.yaw)), RX(ps.roll)), RZ(-ps.pitch));
      const Mh = mul(mul(mul(mul(Mc, T(0.03, 0.62, 0)), RZ(-ps.hp)), RY(ps.hy)), RX(ps.hr));
      const fwd = norm(sub(xf(M, [1, 0, 0]), xf(M, [0, 0, 0])));
      const sk = { M, Mp, Mc, Mh, fwd, S, legs: [], arms: [] };
      [1, -1].forEach((sd, i) => {
        const hip = xf(Mp, [0, -0.04, sd * 0.11]);
        const foot = xf(M, ps.feet[i]);
        const pole = add(add(hip, mulv(fwd, 1.0)), xf(M, [0, 0, sd * 0.1]).map((v, j) => (v - xf(M, [0, 0, 0])[j]) * 0.6));
        const [knee, ank] = ik(hip, foot, 0.45 * S, 0.43 * S, pole);
        sk.legs.push({ hip, knee, ank, sd, toe: ps.toe[i] });
        const sh = xf(Mc, [0, 0.44, sd * 0.24]);
        const hand = ps.handsW ? ps.handsW[i] : xf(M, ps.hands[i]);
        const ep = add(add(sh, xf(Mc, [-0.4, -0.5, sd * 0.9])), mulv(xf(Mc, [0, 0, 0]), -1));
        const [elb, wr] = ik(sh, hand, 0.31 * S, 0.29 * S, ep);
        sk.arms.push({ sh, elb, wr, sd });
      });
      return sk;
    }
    const beltBack = (sk, sd) => xf(sk.Mp, [-0.1, 0.1, sd * 0.15]);
    const beltSide = (sk, sd) => xf(sk.Mp, [0.0, 0.1, sd * 0.22]);
    const chestPt = (sk) => xf(sk.Mc, [0.1, 0.35, 0]);
    const headPt = (sk) => xf(sk.Mh, [0, 0.1, 0]);

    // ---- сурет салу
    function draw(sk, k) {
      const { P, seg, SPH, CYL, TAPER, BOX, I4, mul, T } = G3, W = I4(), s = sk.S;
      const jacket = hex(k.jacket), jacket2 = hex(k.jacket2), trim = hex(k.trim), belt = hex(k.belt), pants = hex(k.pants),
        boot = hex(k.boot), skin = hex(k.skin), skin2 = hex(k.skin2), hair = hex(k.hair), lip = hex(k.lip);
      const eyeW = [0.93, 0.91, 0.87], iris = [0.16, 0.09, 0.05];
      // аяқтар: кең шалбар, мәсі
      sk.legs.forEach((g) => {
        seg(W, g.hip, g.knee, 0.115 * s, pants, "TAPER", 0.05);
        P(W, SPH, g.knee, null, [0.088 * s, 0.088 * s, 0.088 * s], pants, 0.05);
        const mid = lerpV(g.knee, g.ank, 0.35);
        seg(W, g.knee, mid, 0.085 * s, pants, "CYL", 0.05);
        seg(W, mid, g.ank, 0.068 * s, boot, "TAPER", 0.35);
        P(W, SPH, mid, null, [0.08 * s, 0.03 * s, 0.08 * s], boot, 0.3);
        const toe = add(add(g.ank, mulv(sk.fwd, 0.21 * s)), [0, -0.045 * s + g.toe * 0.1, 0]);
        seg(W, add(g.ank, mulv(sk.fwd, -0.04 * s)), toe, 0.058 * s, boot, "SPH", 0.35);
      });
      // жамбас, белбеу
      const Mp = sk.Mp, Mc = sk.Mc, Mh = sk.Mh;
      P(Mp, SPH, [-0.01, 0.0, 0], null, [0.17, 0.15, 0.215], pants, 0.05);
      P(Mp, SPH, [-0.07, -0.02, 0.08], null, [0.1, 0.11, 0.1], pants, 0.05);
      P(Mp, SPH, [-0.07, -0.02, -0.08], null, [0.1, 0.11, 0.1], pants, 0.05);
      // күрте (етек)
      P(Mp, SPH, [0.0, 0.09, 0], null, [0.185, 0.12, 0.235], jacket, 0.08);
      P(Mp, CYL, [0, 0.11, 0], null, [0.2, 0.065, 0.245], belt, 0.25);                  // белбеу
      P(Mp, BOX, [0.19, 0.11, 0.06], [0, 0, 0], [0.04, 0.08, 0.07], belt, 0.25);        // түйін
      seg(Mp, [0.2, 0.09, 0.07], [0.205, -0.06, 0.1], 0.022, belt, "CYL", 0.2);
      seg(Mp, [0.2, 0.09, 0.05], [0.21, -0.05, 0.02], 0.022, belt, "CYL", 0.2);
      // кеуде (күрте), бұлшықеттер
      P(Mc, SPH, [0.02, 0.1, 0], null, [0.19, 0.2, 0.23], jacket, 0.08);                 // іш
      P(Mc, SPH, [0.0, 0.33, 0], null, [0.18, 0.21, 0.27], jacket, 0.08);                // кеуде
      P(Mc, SPH, [-0.06, 0.36, 0], null, [0.15, 0.2, 0.25], jacket2, 0.06);              // арқа
      P(Mc, SPH, [-0.03, 0.48, 0], null, [0.12, 0.08, 0.2], jacket, 0.06);               // трапеция
      P(Mc, SPH, [0.1, 0.5, 0], null, [0.05, 0.05, 0.065], skin, 0.12);               // ашық жаға
      [1, -1].forEach((sd) => P(Mc, SPH, [0.0, 0.44, sd * 0.25], null, [0.092, 0.088, 0.092], jacket, 0.08));   // иық
      // қолдар
      sk.arms.forEach((a) => {
        seg(W, a.sh, a.elb, 0.085 * s, jacket, "TAPER", 0.08);
        P(W, SPH, a.elb, null, [0.07 * s, 0.07 * s, 0.07 * s], jacket, 0.08);
        const cuff = lerpV(a.elb, a.wr, 0.45);
        seg(W, a.elb, cuff, 0.068 * s, jacket, "CYL", 0.08);
        P(W, SPH, cuff, null, [0.07 * s, 0.022 * s, 0.07 * s], trim, 0.1);
        seg(W, cuff, a.wr, 0.052 * s, skin, "TAPER", 0.15);
        const fd = norm(sub(a.wr, a.elb)), hand = add(a.wr, mulv(fd, 0.06 * s));
        seg(W, a.wr, add(hand, mulv(fd, 0.05 * s)), 0.045 * s, skin, "SPH", 0.15);
        P(W, SPH, add(hand, [0, 0.0, 0]), null, [0.048 * s, 0.04 * s, 0.048 * s], skin2, 0.12);  // жұдырық
      });
      // мойын
      seg(Mc, [0.0, 0.5, 0], [0.04, 0.66, 0], 0.075, skin, "CYL", 0.12);
      // бас: қазақ бет-әлпеті — жалпақ бет, айқын бет сүйектері, қысықтау көз
      P(Mh, SPH, [-0.005, 0.1, 0], null, [0.1, 0.12, 0.088], skin, 0.1);               // бас сүйегі
      P(Mh, SPH, [0.05, 0.075, 0], null, [0.062, 0.078, 0.082], skin, 0.12);           // бет
      P(Mh, SPH, [0.04, 0.035, 0], null, [0.072, 0.058, 0.08], skin, 0.1);             // жақ
      P(Mh, SPH, [0.084, 0.012, 0], null, [0.025, 0.022, 0.031], skin, 0.12);          // иек
      [1, -1].forEach((sd) => {
        P(Mh, SPH, [0.068, 0.073, sd * 0.052], null, [0.026, 0.017, 0.024], skin, 0.16);  // бет сүйегі
        P(Mh, SPH, [0.099, 0.098, sd * 0.032], null, [0.011, 0.0055, 0.0135], eyeW, 0.5);   // көз
        P(Mh, SPH, [0.108, 0.0975, sd * 0.031], null, [0.0035, 0.0048, 0.0058], iris, 0.7);
        P(Mh, SPH, [0.103, 0.1025, sd * 0.032], null, [0.0105, 0.0042, 0.0165], skin2, 0.08);  // қабақ
        P(Mh, SPH, [0.1, 0.092, sd * 0.032], null, [0.009, 0.003, 0.015], skin2, 0.05);    // астыңғы қабақ
        P(Mh, SPH, [0.109, 0.116, sd * 0.035], [sd * -0.15, 0, 0], [0.0045, 0.0035, 0.022], hair, 0.05);  // қас
        P(Mh, SPH, [-0.004, 0.083, sd * 0.087], null, [0.021, 0.034, 0.013], skin2, 0.1); // құлақ
        P(Mh, SPH, [0.117, 0.059, sd * 0.011], null, [0.007, 0.006, 0.007], skin2, 0.15); // танау
      });
      P(Mh, SPH, [0.111, 0.085, 0], null, [0.011, 0.024, 0.011], skin, 0.15);          // мұрын қыры
      P(Mh, SPH, [0.123, 0.064, 0], null, [0.013, 0.012, 0.016], skin, 0.2);           // мұрын ұшы
      P(Mh, SPH, [0.112, 0.039, 0], null, [0.006, 0.0055, 0.023], lip, 0.3);           // ерін
      P(Mh, SPH, [0.106, 0.031, 0], null, [0.006, 0.005, 0.019], skin2, 0.2);
      if (k.mustache) P(Mh, SPH, [0.117, 0.049, 0], null, [0.007, 0.006, 0.03], hair, 0.05);
      if (k.beard) { P(Mh, SPH, [0.088, 0.0, 0], null, [0.038, 0.034, 0.045], hair, 0.05); P(Mh, SPH, [0.117, 0.049, 0], null, [0.007, 0.006, 0.03], hair, 0.05); }
      // шаш (қысқа)
      P(Mh, SPH, [-0.012, 0.142, 0], null, [0.103, 0.08, 0.093], hair, 0.15);
      P(Mh, SPH, [0.055, 0.168, 0], null, [0.048, 0.028, 0.078], hair, 0.15);
      P(Mh, SPH, [-0.05, 0.09, 0], null, [0.065, 0.075, 0.087], hair, 0.1);
      if (k.cap) { P(Mh, CYL, [-0.01, 0.2, 0], null, [0.1, 0.04, 0.1], hex(k.cap), 0.2); P(Mh, SPH, [-0.01, 0.22, 0], null, [0.1, 0.035, 0.1], hex(k.cap), 0.2); }
    }

    function shadow(m, x, z, a) { G3.P(m, G3.SPH, [x, 0.012, z], null, [0.45, 0.004, 0.45], [0.1, 0.08, 0.05], 0, a == null ? 0.35 : a); }
    return { S, skeleton, draw, blend, BASEPOSE, beltBack, beltSide, chestPt, headPt, xf, lerpV, add, sub, mulv, norm, shadow };
  })();
  // ================= KURES дене соңы =================
