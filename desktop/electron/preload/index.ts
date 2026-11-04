import { contextBridge, ipcRenderer } from 'electron'
import { IPC_CHANNELS, type DrakterBridge } from '../shared/bridge'

const bridge: DrakterBridge = {
  getAppInfo: () => ipcRenderer.invoke(IPC_CHANNELS.getAppInfo),
  showDesktopNotification: (request) =>
    ipcRenderer.invoke(IPC_CHANNELS.showDesktopNotification, request),
  reportRendererError: (report) => ipcRenderer.invoke(IPC_CHANNELS.reportRendererError, report)
}

contextBridge.exposeInMainWorld('drakter', bridge)
