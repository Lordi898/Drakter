import { useState } from 'react'
import { Button } from '@/components/ui/button'

export function ErrorProbe() {
  const [fail, setFail] = useState(false)
  if (fail) throw new Error('Error de prueba lanzado desde Configuración')
  return (
    <Button type="button" variant="outline" onClick={() => setFail(true)}>
      Provocar un error de prueba
    </Button>
  )
}
