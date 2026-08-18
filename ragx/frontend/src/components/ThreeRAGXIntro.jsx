import React, { useEffect, useRef, useState } from 'react';
import { Zap, ArrowRight, ShieldCheck, Database, FileText, Cpu, CheckCircle } from 'lucide-react';

export default function ThreeRAGXIntro({ onComplete }) {
  const canvasRef = useRef(null);
  const [stage, setStage] = useState(0); // 0: Title, 1: Ingestion, 2: Verification, 3: Complete

  const stagesInfo = [
    { title: "RAGX ENGINE", subtitle: "Data Quality & Factual Reliability Verification Engine" },
    { title: "DOCUMENT INGESTION", subtitle: "Isolated Vector Embeddings & Multi-Chunk Indexing" },
    { title: "PROPOSITION VERIFICATION", subtitle: "Deterministic Claim Verification & Hallucination Defense" },
    { title: "SYSTEM READY", subtitle: "Secure Workspace & Isolated Knowledge Base Active" },
  ];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // Particle System
    const particles = [];
    const particleCount = 70;
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        z: Math.random() * 800 + 100,
        radius: Math.random() * 2 + 1,
        color: Math.random() > 0.5 ? '#38bdf8' : '#818cf8',
        vx: (Math.random() - 0.5) * 1.5,
        vy: (Math.random() - 0.5) * 1.5,
        vz: (Math.random() - 0.5) * 2,
      });
    }

    // Thunder / Lightning Arc Generator
    let lightningArcs = [];
    const generateLightning = (x1, y1, x2, y2, displace) => {
      if (displace < 4) {
        lightningArcs.push({ x1, y1, x2, y2 });
      } else {
        const midX = (x1 + x2) / 2 + (Math.random() - 0.5) * displace;
        const midY = (y1 + y2) / 2 + (Math.random() - 0.5) * displace;
        generateLightning(x1, y1, midX, midY, displace / 2);
        generateLightning(midX, midY, x2, y2, displace / 2);
      }
    };

    let frame = 0;

    const render = () => {
      frame++;
      ctx.fillStyle = 'rgba(2, 6, 23, 0.35)'; // Dark Slate 950 with trailing
      ctx.fillRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // Render Floating 3D Grid & Particle Nodes
      ctx.lineWidth = 1;
      particles.forEach((p, idx) => {
        p.x += p.vx;
        p.y += p.vy;
        p.z += p.vz;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;
        if (p.z < 50 || p.z > 1000) p.vz *= -1;

        const scale = 400 / p.z;
        const px = (p.x - centerX) * scale + centerX;
        const py = (p.y - centerY) * scale + centerY;

        ctx.beginPath();
        ctx.arc(px, py, Math.max(1, p.radius * scale), 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 10;
        ctx.fill();

        // Connect nearby nodes with energy lines
        for (let j = idx + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(px, py);
            const scale2 = 400 / p2.z;
            ctx.lineTo((p2.x - centerX) * scale2 + centerX, (p2.y - centerY) * scale2 + centerY);
            ctx.strokeStyle = `rgba(56, 189, 248, ${0.3 * (1 - dist / 120)})`;
            ctx.stroke();
          }
        }
      });
      ctx.shadowBlur = 0;

      // Render Thunder / Electric Energy Arcs periodically
      if (frame % 25 === 0 || Math.random() < 0.15) {
        lightningArcs = [];
        const startX = centerX + (Math.random() - 0.5) * 400;
        const startY = centerY - 180 + (Math.random() - 0.5) * 100;
        const endX = centerX + (Math.random() - 0.5) * 500;
        const endY = centerY + 180 + (Math.random() - 0.5) * 100;
        generateLightning(startX, startY, endX, endY, 60);
      }

      ctx.beginPath();
      ctx.strokeStyle = 'rgba(125, 211, 252, 0.85)';
      ctx.lineWidth = 2;
      ctx.shadowColor = '#0284c7';
      ctx.shadowBlur = 15;
      lightningArcs.forEach((arc) => {
        ctx.moveTo(arc.x1, arc.y1);
        ctx.lineTo(arc.x2, arc.y2);
      });
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Central Pulsing Electric Core Ring
      const pulse = Math.sin(frame * 0.05) * 15;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 140 + pulse, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(99, 102, 241, 0.4)';
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX, centerY, 180 - pulse, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.3)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    // Stage Auto-advance timer
    const interval = setInterval(() => {
      setStage((prev) => (prev < 3 ? prev + 1 : prev));
    }, 2500);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="relative w-full h-screen bg-slate-950 overflow-hidden select-none flex flex-col justify-between items-center text-slate-100 font-sans">
      <canvas ref={canvasRef} className="absolute inset-0 z-0" />

      {/* Top Header */}
      <div className="relative z-10 w-full p-6 flex justify-between items-center max-w-7xl">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-indigo-500 to-purple-600 p-[2px] shadow-lg shadow-cyan-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Zap className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
          </div>
          <span className="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-400">
            RAGX
          </span>
        </div>

        <button
          onClick={onComplete}
          className="flex items-center space-x-2 px-5 py-2.5 rounded-full bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/60 backdrop-blur-md transition-all duration-200 text-sm font-medium shadow-lg hover:border-cyan-500/50 cursor-pointer"
        >
          <span>Skip Intro</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Center 3D Title Overlay */}
      <div className="relative z-10 flex flex-col items-center justify-center text-center px-4 max-w-4xl my-auto">
        <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 backdrop-blur-md mb-6 shadow-xl shadow-cyan-950/40">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-semibold text-cyan-300 tracking-wider uppercase">
            Phase 3 Certified • Deterministic Evaluation
          </span>
        </div>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-4 drop-shadow-[0_10px_20px_rgba(0,0,0,0.8)]">
          {stagesInfo[stage].title}
        </h1>

        <p className="text-lg md:text-xl text-slate-300 font-normal max-w-2xl leading-relaxed mb-8 drop-shadow-md">
          {stagesInfo[stage].subtitle}
        </p>

        {/* Feature Highlights Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-3xl my-4">
          <div className={`p-4 rounded-xl border backdrop-blur-md transition-all duration-300 ${stage >= 0 ? 'bg-slate-900/80 border-cyan-500/50 text-cyan-300 shadow-lg shadow-cyan-950/50' : 'bg-slate-900/30 border-slate-800 text-slate-500'}`}>
            <Cpu className="w-6 h-6 mx-auto mb-2 text-cyan-400" />
            <div className="text-xs font-semibold">Deterministic Logic</div>
          </div>
          <div className={`p-4 rounded-xl border backdrop-blur-md transition-all duration-300 ${stage >= 1 ? 'bg-slate-900/80 border-indigo-500/50 text-indigo-300 shadow-lg shadow-indigo-950/50' : 'bg-slate-900/30 border-slate-800 text-slate-500'}`}>
            <Database className="w-6 h-6 mx-auto mb-2 text-indigo-400" />
            <div className="text-xs font-semibold">User Data Isolation</div>
          </div>
          <div className={`p-4 rounded-xl border backdrop-blur-md transition-all duration-300 ${stage >= 2 ? 'bg-slate-900/80 border-purple-500/50 text-purple-300 shadow-lg shadow-purple-950/50' : 'bg-slate-900/30 border-slate-800 text-slate-500'}`}>
            <FileText className="w-6 h-6 mx-auto mb-2 text-purple-400" />
            <div className="text-xs font-semibold">5-Tuple Citations</div>
          </div>
          <div className={`p-4 rounded-xl border backdrop-blur-md transition-all duration-300 ${stage >= 3 ? 'bg-slate-900/80 border-emerald-500/50 text-emerald-300 shadow-lg shadow-emerald-950/50' : 'bg-slate-900/30 border-slate-800 text-slate-500'}`}>
            <CheckCircle className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
            <div className="text-xs font-semibold">Zero Hallucinations</div>
          </div>
        </div>

        <button
          onClick={onComplete}
          className="mt-8 group relative inline-flex items-center space-x-3 px-8 py-4 rounded-2xl bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-600 text-white font-bold text-lg shadow-2xl shadow-cyan-500/30 hover:shadow-cyan-500/50 hover:scale-105 transition-all duration-300 cursor-pointer"
        >
          <span>Enter RAGX Application</span>
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      {/* Bottom Stage Progress Indicator */}
      <div className="relative z-10 w-full p-6 flex justify-center items-center space-x-3">
        {stagesInfo.map((_, idx) => (
          <div
            key={idx}
            onClick={() => setStage(idx)}
            className={`h-2 rounded-full cursor-pointer transition-all duration-300 ${
              stage === idx ? 'w-10 bg-cyan-400 shadow-md shadow-cyan-400/50' : 'w-2 bg-slate-700 hover:bg-slate-500'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
