/**
 * Panel principal PROVISIONAL de un sector aún sin portar (paso 2 del plan, visor-port.md §5):
 * mantiene el cilindro completo (periferia y navegación) mientras llegan los sectores con datos reales.
 */
import { Panel } from '../Panel'
import { FAR } from '../stage/world'

export function SectorStub({ sector, name }: { readonly sector: number; readonly name: string }) {
  return (
    <Panel sector={sector} R={FAR} y={30} w={780} h={560} title={name} code={`SEC-${sector}`}>
      <p className="jv-visor-note">Este sector se está portando al modo Jarvis. Mientras tanto, la misma sección está completa en Drakter.</p>
    </Panel>
  )
}
