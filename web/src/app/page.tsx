import Link from "next/link";

/* ─── Helpers ────────────────────────────────────────────────────────────── */

function Dot() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-1 w-1 rounded-full"
      style={{ background: "#c4bfb5" }}
    />
  );
}

/* ─── Landing page ───────────────────────────────────────────────────────── */

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* ── Header / Nav ─────────────────────────────────────────────────── */}
      <header className="border-b border-linea bg-papel">
        <div
          className="mx-auto px-10"
          style={{
            maxWidth: 1180,
            padding: "0 40px",
            height: 60,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 24,
          }}
        >
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              className="font-serif text-tinta"
              style={{ fontSize: 17, fontWeight: 600 }}
            >
              Copiloto Normativo
            </span>
            <span
              className="font-mono text-guinda"
              style={{
                fontSize: 9,
                fontWeight: 600,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                border: "1px solid #6E1423",
                padding: "2px 6px",
              }}
            >
              BETA
            </span>
          </div>

          {/* Nav links */}
          <nav
            style={{ display: "flex", alignItems: "center", gap: 28 }}
            aria-label="Navegación principal"
          >
            <a
              href="#como-funciona"
              className="font-sans text-masa"
              style={{ fontSize: 13.5, textDecoration: "none" }}
            >
              Cómo funciona
            </a>
            <a
              href="#ejemplo"
              className="font-sans text-masa"
              style={{ fontSize: 13.5, textDecoration: "none" }}
            >
              Ejemplo
            </a>
            <Link
              href="/app"
              className="font-sans"
              style={{
                fontSize: 13.5,
                fontWeight: 600,
                color: "#F6F5F1",
                background: "#6E1423",
                padding: "7px 18px",
                textDecoration: "none",
              }}
            >
              Probar la demo
            </Link>
          </nav>
        </div>
      </header>

      {/* ── §1 Hero ──────────────────────────────────────────────────────── */}
      <section>
        <div
          className="mx-auto px-10"
          style={{ maxWidth: 1180, paddingTop: 96, paddingBottom: 88 }}
        >
          <div style={{ maxWidth: 860 }}>
            {/* Eyebrow */}
            <p
              className="font-mono text-guinda"
              style={{
                fontSize: 12,
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                marginBottom: 26,
              }}
            >
              Asistente de IA · Documentos legales y regulatorios de México
            </p>

            {/* Headline */}
            <h1
              className="font-serif text-tinta text-balance"
              style={{
                fontWeight: 700,
                fontSize: 66,
                lineHeight: 1.05,
                letterSpacing: "-0.02em",
              }}
            >
              Pregúntale a la ley.
              <br />
              Responde citando la fuente exacta.
            </h1>

            {/* Sub */}
            <p
              className="text-pretty"
              style={{
                marginTop: 30,
                fontSize: 20,
                lineHeight: 1.6,
                color: "#3a3a38",
                maxWidth: 660,
              }}
            >
              Sube un documento regulatorio y pregúntale en lenguaje natural.
              Copiloto Normativo responde citando la fuente exacta —artículo y
              página—{" "}
              <strong style={{ color: "#111110", fontWeight: 600 }}>
                y nunca inventa
              </strong>
              .
            </p>

            {/* CTAs */}
            <div
              style={{
                marginTop: 40,
                display: "flex",
                alignItems: "center",
                gap: 22,
                flexWrap: "wrap",
              }}
            >
              <Link
                href="/app"
                className="font-sans"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: "#F6F5F1",
                  background: "#6E1423",
                  padding: "16px 34px",
                  borderRadius: 3,
                  boxShadow: "0 1px 0 rgba(17,17,16,0.08)",
                  textDecoration: "none",
                }}
              >
                Probar la demo →
              </Link>
              <a
                href="#ejemplo"
                className="font-sans"
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: "#6E1423",
                  textDecoration: "none",
                }}
              >
                Ver una respuesta de ejemplo
              </a>
            </div>
          </div>

          {/* Stats strip */}
          <div
            className="border-t border-linea"
            style={{
              marginTop: 72,
              paddingTop: 22,
              display: "flex",
              gap: 56,
              flexWrap: "wrap",
            }}
          >
            {[
              {
                title: "Cero alucinaciones",
                body: "Toda afirmación va anclada a un fragmento verificable del documento.",
              },
              {
                title: "Cita a nivel artículo",
                body: "Artículo, fracción y página. Comprueba la fuente en un clic.",
              },
              {
                title: "Lenguaje natural",
                body: "Pregunta como le preguntarías a un abogado. Sin operadores ni sintaxis.",
              },
            ].map(({ title, body }) => (
              <div key={title} style={{ maxWidth: 220 }}>
                <p
                  className="font-serif text-tinta"
                  style={{ fontSize: 15, fontWeight: 600 }}
                >
                  {title}
                </p>
                <p
                  style={{
                    fontSize: 13.5,
                    lineHeight: 1.55,
                    color: "#57564f",
                    marginTop: 5,
                  }}
                >
                  {body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── §2 Cómo funciona ─────────────────────────────────────────────── */}
      <section
        id="como-funciona"
        className="border-t border-b border-linea"
        style={{ background: "#F1EFE9" }}
      >
        <div className="mx-auto px-10" style={{ maxWidth: 1180, padding: "88px 40px" }}>
          {/* Section header */}
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 16,
              marginBottom: 56,
            }}
          >
            <h2
              className="font-serif text-tinta"
              style={{ fontWeight: 700, fontSize: 38, letterSpacing: "-0.015em" }}
            >
              Cómo funciona
            </h2>
            <span
              className="font-mono"
              style={{
                fontSize: 12,
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "#8a887f",
              }}
            >
              Tres pasos
            </span>
          </div>

          {/* 3-column grid with 1px gap effect */}
          <div
            className="border border-linea"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0,1fr))",
              gap: 1,
              background: "#D8D4CC",
            }}
          >
            {[
              {
                num: "§1",
                title: "Sube el documento",
                body: "Arrastra una ley, reglamento, NOM o contrato en PDF. Se indexa por artículos y páginas en segundos.",
              },
              {
                num: "§2",
                title: "Pregunta en lenguaje natural",
                body: '"¿Qué plazo tengo para presentar la declaración?" Escribe como hablas; sin palabras clave ni sintaxis.',
              },
              {
                num: "§3",
                title: "Recibe la respuesta con su cita",
                body: "Una respuesta clara acompañada del artículo, la página y el fragmento textual que la respalda.",
              },
            ].map(({ num, title, body }) => (
              <div key={num} className="bg-papel" style={{ padding: "40px 34px 44px" }}>
                <p
                  className="font-serif text-guinda"
                  style={{ fontSize: 34, fontWeight: 600 }}
                >
                  {num}
                </p>
                <div className="border-t border-linea" style={{ margin: "20px 0 22px" }} />
                <h3
                  className="font-serif text-tinta"
                  style={{ fontSize: 22, fontWeight: 600 }}
                >
                  {title}
                </h3>
                <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "#57564f", marginTop: 12 }}>
                  {body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── §3 Ejemplo de respuesta ──────────────────────────────────────── */}
      <section id="ejemplo">
        <div className="mx-auto px-10" style={{ maxWidth: 1180, padding: "96px 40px" }}>
          {/* Section header */}
          <div style={{ maxWidth: 640, marginBottom: 52 }}>
            <p
              className="font-mono text-guinda"
              style={{
                fontSize: 12,
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                marginBottom: 18,
              }}
            >
              Así se ve una respuesta
            </p>
            <h2
              className="font-serif text-tinta"
              style={{
                fontWeight: 700,
                fontSize: 38,
                letterSpacing: "-0.015em",
                lineHeight: 1.1,
              }}
            >
              Cada respuesta viene con su expediente.
            </h2>
            <p
              className="text-pretty"
              style={{ fontSize: 17, lineHeight: 1.6, color: "#3a3a38", marginTop: 18 }}
            >
              No un párrafo genérico: la afirmación, y debajo la fuente textual
              que la sustenta. Puedes verificarla sin salir de la conversación.
            </p>
          </div>

          {/* Mock chat card */}
          <div
            className="bg-papel border border-linea"
            style={{
              maxWidth: 820,
              borderRadius: 5,
              overflow: "hidden",
              boxShadow: "0 20px 50px -30px rgba(17,17,16,0.35)",
            }}
          >
            {/* Question row */}
            <div
              className="border-b border-linea"
              style={{
                padding: "24px 30px",
                display: "flex",
                gap: 14,
                alignItems: "flex-start",
              }}
            >
              <span
                className="font-mono"
                style={{
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  color: "#8a887f",
                  textTransform: "uppercase",
                  paddingTop: 3,
                  flexShrink: 0,
                }}
              >
                Tú
              </span>
              <p
                className="text-tinta"
                style={{ fontSize: 16, lineHeight: 1.55, fontWeight: 500 }}
              >
                ¿Cuál es el plazo para presentar la declaración anual de personas
                físicas?
              </p>
            </div>

            {/* Answer row */}
            <div style={{ padding: "26px 30px 30px" }}>
              <span
                className="font-mono text-guinda"
                style={{
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  display: "block",
                  marginBottom: 14,
                }}
              >
                Copiloto
              </span>
              <p className="text-tinta" style={{ fontSize: 16.5, lineHeight: 1.65 }}>
                Las personas físicas deben presentar su declaración anual{" "}
                <strong style={{ fontWeight: 600 }}>durante el mes de abril</strong>{" "}
                del año siguiente al que corresponda el ejercicio.
              </p>

              {/* Citation card */}
              <div
                className="border border-linea"
                style={{
                  marginTop: 22,
                  borderLeft: "3px solid #6E1423",
                  borderRadius: 3,
                  background: "#F1EFE9",
                }}
              >
                {/* Citation header */}
                <div
                  className="border-b border-linea"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    padding: "12px 18px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      flexWrap: "wrap",
                    }}
                  >
                    <span
                      className="font-mono text-guinda"
                      style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.02em" }}
                    >
                      Art. 150
                    </span>
                    <Dot />
                    <span style={{ fontSize: 12.5, color: "#57564f" }}>
                      Ley del Impuesto sobre la Renta
                    </span>
                    <Dot />
                    <span style={{ fontSize: 12.5, color: "#57564f" }}>pág. 187</span>
                  </div>
                  <a
                    href="#"
                    className="font-mono text-guinda"
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.06em",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      flexShrink: 0,
                      textDecoration: "none",
                    }}
                  >
                    Ver fuente ↗
                  </a>
                </div>

                {/* Blockquote */}
                <blockquote
                  className="font-serif"
                  style={{
                    padding: "16px 18px",
                    fontStyle: "italic",
                    fontSize: 15.5,
                    lineHeight: 1.6,
                    color: "#3a3a38",
                  }}
                >
                  "Las personas físicas que obtengan ingresos en un año de
                  calendario […] están obligadas a pagar su impuesto anual
                  mediante declaración que presentarán en el mes de abril del año
                  siguiente."
                </blockquote>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── §4 Stack técnico ─────────────────────────────────────────────── */}
      <section className="border-t border-linea">
        <div
          className="mx-auto px-10"
          style={{
            maxWidth: 1180,
            padding: "34px 40px",
            display: "flex",
            alignItems: "center",
            gap: 28,
            flexWrap: "wrap",
            justifyContent: "space-between",
          }}
        >
          <span
            className="font-mono"
            style={{
              fontSize: 11,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "#8a887f",
            }}
          >
            Construido con
          </span>
          <div
            style={{ display: "flex", alignItems: "center", gap: 26, flexWrap: "wrap" }}
          >
            {["FastAPI", "PostgreSQL + pgvector", "Next.js", "Groq"].map(
              (tech, i, arr) => (
                <span key={tech} style={{ display: "flex", alignItems: "center", gap: 26 }}>
                  <span
                    className="font-mono"
                    style={{ fontSize: 14, color: "#3a3a38" }}
                  >
                    {tech}
                  </span>
                  {i < arr.length - 1 && <Dot />}
                </span>
              ),
            )}
          </div>
        </div>
      </section>

      {/* ── §5 CTA final ─────────────────────────────────────────────────── */}
      <section id="demo" className="bg-guinda">
        <div
          className="mx-auto px-10 text-center"
          style={{ maxWidth: 1180, padding: "96px 40px" }}
        >
          <h2
            className="font-serif text-balance mx-auto"
            style={{
              fontWeight: 700,
              fontSize: 46,
              lineHeight: 1.1,
              letterSpacing: "-0.015em",
              color: "#F6F5F1",
              maxWidth: 760,
            }}
          >
            Deja de leer 300 páginas para encontrar un párrafo.
          </h2>
          <p
            className="text-pretty mx-auto"
            style={{
              fontSize: 18,
              lineHeight: 1.6,
              color: "#e8d6d9",
              margin: "22px auto 0",
              maxWidth: 560,
            }}
          >
            Sube tu documento, haz tu pregunta y recibe la respuesta con la cita
            exacta. Pruébalo ahora mismo.
          </p>
          <div style={{ marginTop: 38 }}>
            <Link
              href="/app"
              className="font-sans inline-block"
              style={{
                fontSize: 17,
                fontWeight: 600,
                color: "#6E1423",
                background: "#F6F5F1",
                padding: "17px 40px",
                borderRadius: 3,
                textDecoration: "none",
              }}
            >
              Probar la demo →
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="bg-guinda" style={{ borderTop: "1px solid #58101C" }}>
        <div
          className="mx-auto px-10"
          style={{
            maxWidth: 1180,
            padding: "26px 40px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            flexWrap: "wrap",
          }}
        >
          <span className="font-serif" style={{ fontSize: 15, fontWeight: 600, color: "#F6F5F1" }}>
            Copiloto Normativo
          </span>
          <span style={{ fontSize: 12.5, color: "#e0c4c9" }}>
            Responde citando la fuente. Nunca inventa.
          </span>
        </div>
      </footer>
    </div>
  );
}
