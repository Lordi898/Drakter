export function StorageDrawing() {
  return (
    <svg
      width="220"
      height="130"
      viewBox="0 0 220 130"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
    >
      {/* cuerpo del mueble */}
      <rect x="50" y="10" width="120" height="104" />
      {/* zócalo y patas */}
      <path d="M44 114H176" />
      <path d="M58 114v8M162 114v8" />
      {/* cajones */}
      <path d="M58 18h104v28H58zM58 50h104v28H58zM58 82h104v26H58z" />
      {/* tiradores */}
      <path d="M99 32h22M99 64h22M99 95h22" />
      {/* cotas */}
      <path d="M30 10v104M26 10h8M26 114h8" strokeDasharray="3 3" />
      <path d="M50 126h120M50 122v8M170 122v8" strokeDasharray="3 3" />
    </svg>
  )
}
