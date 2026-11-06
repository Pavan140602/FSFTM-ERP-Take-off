      if (m.type === 'legend' && m.points.length >= 1) {
        // Placed legend, drawn from its own properties (Revu): font, title
        // and cell sizes / styles / colours, opacity, line colour / width /
        // style, fill and fill opacity. The whole box scales with its stored
        // width (OE-DELIVERY 2026-11-12-revu-ui).
        const p = m.points[0]!;
        const rows = getPlacedLegendRowsRef.current(m);
        const cols = legendColsForRef.current(m);
        const lSetup = m.legendSetup;
        const look = legendLook(lSetup, {
          text: legendTextColorRef.current,
          bg: legendBgColorRef.current,
          border: legendBorderStyleRef.current,
        });
        const showTitle = lSetup?.showTitle !== false;
        const met = legendMetrics(lSetup, legendPadTop + legendPadBottom);
        const lx = p.x * dpr * zoom;
        const ly = p.y * dpr * zoom;
        const userW = m.width && m.width > 0 ? m.width : 0;
        const k = dpr * zoom;
        // Column widths at scale 1 (PDF units): header and every value.
        const typeColW = (24 + 24 * met.cf) + legendPadLeft + legendPadRight;
        const colWidths: number[] = cols.map((col) => {
          ctx.font = legendFont({ ...look.cell, bold: true }, (look.cell.size - 1) * k, look.font);
          let w = ctx.measureText(col.label).width / k;
          ctx.font = legendFont(look.cell, look.cell.size * k, look.font);
          for (const row of rows) {
            const val = String(row.cells[col.key] ?? '—').slice(0, 24);
            w = Math.max(w, ctx.measureText(val).width / k);
          }
          return Math.max(36, w + 16 + legendPadLeft + legendPadRight);
        });
        const colXOffsets: number[] = [];
        let acc = typeColW;
        for (const w of colWidths) {
          colXOffsets.push(acc);
          acc += w;
        }
        if (showTitle) {
          ctx.font = legendFont(look.title, look.title.size * k, look.font);
          acc = Math.max(acc, ctx.measureText(lSetup?.title || 'Legend').width / k + 24);
        }
        const autoW = Math.max(120, acc + 12);
        legendAutoWidthRef.current.set(m.id, autoW);
        const cs = userW > 0 ? Math.min(4, Math.max(0.25, userW / Math.max(autoW, 1))) : 1;
        const S = cs * k; // PDF units -> canvas px
        const lw = autoW * S;
        const headerH = showTitle ? met.titleH * S : 0;
        const colHeaderH = met.colH * S;
        const rowH = met.rowH * S;
        const totalHeaderH = headerH + colHeaderH;
        const lh = (legendTotalHeight(rows.length, met, showTitle)) * S;
        const isSel = m.id === selectedMeasurementId;
        ctx.save();
        ctx.globalAlpha = look.opacity;
        // Fill (background) with its own opacity.
        if (look.fill) {
          ctx.save();
          ctx.globalAlpha = look.opacity * look.fillOpacity;
          ctx.fillStyle = look.fill;
          ctx.fillRect(lx, ly, lw, lh);
          ctx.restore();
        }
        // Title.
        const underline = (x0: number, x1: number, y: number, color: string, px: number) => {
          ctx.strokeStyle = color;
          ctx.lineWidth = Math.max(1, px / 14);
          ctx.beginPath();
          ctx.moveTo(x0, y);
          ctx.lineTo(x1, y);
          ctx.stroke();
        };
        ctx.textBaseline = 'middle';
        if (showTitle) {
          const tpx = look.title.size * S;
          ctx.font = legendFont(look.title, tpx, look.font);
          ctx.fillStyle = look.title.color;
          ctx.textAlign = 'center';
          const tt = lSetup?.title || 'Legend';
          ctx.fillText(tt, lx + lw / 2, ly + headerH / 2);
          if (look.title.underline) {
            const tw = ctx.measureText(tt).width;
            underline(lx + lw / 2 - tw / 2, lx + lw / 2 + tw / 2, ly + headerH / 2 + tpx * 0.55, look.title.color, tpx);
          }
        }
        // Column labels.
        const colX = (idx: number) => lx + colXOffsets[idx]! * S;
        const colW = (idx: number) => colWidths[idx]! * S;
        const hpx = (look.cell.size - 1) * S;
        ctx.font = legendFont({ ...look.cell, bold: true }, hpx, look.font);
        ctx.fillStyle = look.cell.color;
        cols.forEach((col, idx) => {
          const x = colX(idx);
          if (col.align === 'right') {
            ctx.textAlign = 'right';
            ctx.fillText(col.label, x + colW(idx) - (6 + legendPadRight) * S, ly + headerH + colHeaderH / 2);
          } else {
            ctx.textAlign = 'left';
            ctx.fillText(col.label, x + legendPadLeft * S, ly + headerH + colHeaderH / 2);
          }
        });
        // Rows.
        ctx.save();
        ctx.beginPath();
        ctx.rect(lx, ly + totalHeaderH, lw, Math.max(0, lh - totalHeaderH));
        ctx.clip();
        const cpx = look.cell.size * S;
        rows.forEach((row, i) => {
          const ry = ly + totalHeaderH + i * rowH;
          const sw = 12 * met.cf * S;
          ctx.fillStyle = row.color;
          ctx.fillRect(lx + (10 + legendPadLeft) * S, ry + (rowH - sw) / 2, sw, sw);
          ctx.strokeStyle = '#9ca3af';
          ctx.lineWidth = 1 * dpr;
          ctx.strokeRect(lx + (10 + legendPadLeft) * S, ry + (rowH - sw) / 2, sw, sw);
          drawLegendTypeSymbol(ctx, row.type, lx + (10 + 18 * met.cf + legendPadLeft) * S, ry + (rowH - sw) / 2, sw, look.cell.color);
          ctx.font = legendFont(look.cell, cpx, look.font);
          cols.forEach((col, idx) => {
            ctx.fillStyle = look.cell.color;
            const val = String(row.cells[col.key] ?? '—').slice(0, 24);
            const x = colX(idx);
            let x0: number;
            if (col.align === 'right') {
              ctx.textAlign = 'right';
              const xr = x + colW(idx) - (6 + legendPadRight) * S;
              ctx.fillText(val, xr, ry + rowH / 2);
              x0 = xr - ctx.measureText(val).width;
            } else {
              ctx.textAlign = 'left';
              x0 = x + legendPadLeft * S;
              ctx.fillText(val, x0, ry + rowH / 2);
            }
            if (look.cell.underline) underline(x0, x0 + ctx.measureText(val).width, ry + rowH / 2 + cpx * 0.55, look.cell.color, cpx);
          });
        });
        ctx.restore();
        ctx.textAlign = 'left';
        // Table lines in the legend style, line colour and width.
        const borderStyle = look.border;
        if (borderStyle !== 'none' && look.lineWidth > 0) {
          ctx.strokeStyle = look.lineColor;
          ctx.lineWidth = Math.max(0.5, look.lineWidth * S * 0.75);
          ctx.beginPath();
          if (borderStyle === 'outline' || borderStyle === 'grid') ctx.rect(lx, ly, lw, lh);
          if (showTitle && (borderStyle === 'grid' || borderStyle === 'horizontal')) {
            ctx.moveTo(lx, ly + headerH);
            ctx.lineTo(lx + lw, ly + headerH);
          }
          if (borderStyle === 'horizontal' || borderStyle === 'grid') {
            ctx.moveTo(lx, ly + totalHeaderH);
            ctx.lineTo(lx + lw, ly + totalHeaderH);
            rows.forEach((_, i) => {
              const ry = ly + totalHeaderH + (i + 1) * rowH;
              if (ry < ly + lh - 1) {
                ctx.moveTo(lx, ry);
                ctx.lineTo(lx + lw, ry);
              }
            });
          }
          if (borderStyle === 'vertical' || borderStyle === 'grid') {
            cols.forEach((_, idx) => {
              const x = colX(idx);
              ctx.moveTo(x, ly + headerH);
              ctx.lineTo(x, ly + lh);
            });
          }
          ctx.stroke();
        }
        ctx.restore();
        // Selection frame + resize dots (fixed screen size).
        if (isSel) {
          ctx.strokeStyle = '#2563eb';
          ctx.lineWidth = 1.5 * dpr;
          ctx.setLineDash([4 * dpr, 3 * dpr]);
          ctx.strokeRect(lx, ly, lw, lh);
          ctx.setLineDash([]);
          const dotR = 5 * dpr;
          ctx.fillStyle = '#2563eb';
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1.5 * dpr;
          for (const [dx, dy] of [[lx, ly], [lx + lw, ly], [lx + lw, ly + lh], [lx, ly + lh]] as const) {
            ctx.beginPath();
            ctx.arc(dx, dy, dotR, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
          }
        }
        ctx.lineWidth = 2 * dpr;
        ctx.textBaseline = 'alphabetic';
      }

