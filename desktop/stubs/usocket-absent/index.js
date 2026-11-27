// Stub de Drakter: usocket (nativo, con node-gyp) no se usa. dbus-next captura este error
// en direcciones unix:path= y abre el bus con net.createConnection. Ver docs/DECISIONS.md.
throw new Error('usocket no está disponible en Drakter: dbus-next usa net.createConnection')
