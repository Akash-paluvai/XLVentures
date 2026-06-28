import { create } from 'zustand'

export const useAppStore = create((set) => ({
  activeDomain: 'customer_success',
  setActiveDomain: (domain) => set({ activeDomain: domain }),
}))
