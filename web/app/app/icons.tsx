// Ícones de linha monocromaticos (combinam com o 8-bit; sem emoji colorido).
type P = { size?: number };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function Icon({ name, size = 20 }: { name: string } & P) {
  switch (name) {
    case "home":
      return (
        <svg {...base(size)}>
          <path d="M4 11l8-7 8 7" />
          <path d="M6 10v9h12v-9" />
        </svg>
      );
    case "library":
      return (
        <svg {...base(size)}>
          <rect x="3" y="4" width="8" height="7" />
          <rect x="13" y="4" width="8" height="7" />
          <rect x="3" y="14" width="8" height="6" />
          <rect x="13" y="14" width="8" height="6" />
        </svg>
      );
    case "key":
      return (
        <svg {...base(size)}>
          <circle cx="8" cy="8" r="4" />
          <path d="M11 11l8 8M16 16l2-2M18 18l2-2" />
        </svg>
      );
    case "user":
      return (
        <svg {...base(size)}>
          <circle cx="12" cy="8" r="4" />
          <path d="M5 20c0-3.5 3-6 7-6s7 2.5 7 6" />
        </svg>
      );
    case "logout":
      return (
        <svg {...base(size)}>
          <path d="M14 4H6v16h8" />
          <path d="M11 12h9M17 8l4 4-4 4" />
        </svg>
      );
    case "link":
      return (
        <svg {...base(size)}>
          <path d="M9 15l6-6" />
          <path d="M8 11l-2 2a3 3 0 0 0 4 4l2-2" />
          <path d="M16 13l2-2a3 3 0 0 0-4-4l-2 2" />
        </svg>
      );
    case "spark":
      return (
        <svg {...base(size)}>
          <path d="M12 3l1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6z" />
        </svg>
      );
    case "cc":
      return (
        <svg {...base(size)}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="M10 10a2 2 0 1 0 0 4M16 10a2 2 0 1 0 0 4" />
        </svg>
      );
    case "crop":
      return (
        <svg {...base(size)}>
          <path d="M7 3v14h14M3 7h14v14" />
        </svg>
      );
    case "chart":
      return (
        <svg {...base(size)}>
          <path d="M4 20V4M4 20h16" />
          <path d="M8 16v-4M12 16V8M16 16v-7" />
        </svg>
      );
    case "script":
      return (
        <svg {...base(size)}>
          <path d="M6 3h9l4 4v14H6z" />
          <path d="M14 3v5h5M9 12h7M9 16h7" />
        </svg>
      );
    case "face":
      return (
        <svg {...base(size)}>
          <circle cx="12" cy="12" r="9" />
          <path d="M9 10h.01M15 10h.01M8.5 15c1 1 5 1 7 0" />
        </svg>
      );
    case "coin":
      return (
        <svg {...base(size)}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v10M14.5 9.5c0-1.2-1.1-2-2.5-2s-2.5.8-2.5 2 1.1 1.8 2.5 1.8 2.5.8 2.5 2-1.1 2-2.5 2-2.5-.8-2.5-2" />
        </svg>
      );
    case "film":
      return (
        <svg {...base(size)}>
          <rect x="3" y="4" width="18" height="16" rx="1" />
          <path d="M3 9h18M3 15h18M8 4v16M16 4v16" />
        </svg>
      );
    default:
      return null;
  }
}
