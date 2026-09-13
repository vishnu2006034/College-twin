import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('unauthenticated visitor gets a labelled login and no invented dashboard metrics', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({message:'Sign in required'}) }))
  render(<App/>);
  expect(await screen.findByRole('button', {name: 'Sign in →'})).toBeVisible()
  expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password')
  expect(screen.queryByText('Rooms in edition')).not.toBeInTheDocument()
})

test('failed login gives an actionable error and can be retried', async () => {
  const fetcher = vi.fn().mockResolvedValue({ok:false,status:401,json:async()=>({message:'Invalid username or password'})})
  vi.stubGlobal('fetch', fetcher)
  render(<App/>);
  fireEvent.change(await screen.findByLabelText('Username'), {target:{value:'planner'}})
  fireEvent.change(screen.getByLabelText('Password'), {target:{value:'wrong'}})
  fireEvent.click(screen.getByRole('button', {name:'Sign in →'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password')
  await waitFor(() => expect(screen.getByRole('button', {name:'Sign in →'})).toBeEnabled())
})

test('empty authenticated workspace explains how to load data', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url:string) => Promise.resolve({
    ok:true,status:200,json:async()=>url.endsWith('/auth/me') ? {id:'1',username:'viewer',role:'viewer'} : {items:[],total:0},
  })))
  render(<App/>);
  fireEvent.click(await screen.findByText('Dataset workspace & room inventory'))
  expect(await screen.findByText(/No frozen datasets/)).toBeVisible()
  expect(screen.getByText(/Frontend work begins/)).toHaveTextContent('week 4')
})

test('room API failure leaves the campus usable and displays the error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(
    url.includes('/rooms?') ? { ok: false, status: 503, json: async () => ({ message: 'Room service unavailable' }) } :
    { ok: true, status: 200, json: async () => url.endsWith('/auth/me') ? { id: '1', username: 'viewer', role: 'viewer' } : { items: [{ id: 'edition-a', seed: 42, config: { weeks: 16 }, generator_version: '1' }], total: 1 } }
  )))
  render(<App/> )
  expect(await screen.findByRole('alert')).toHaveTextContent('Room service unavailable')
  fireEvent.click(screen.getByRole('button', { name: 'Explore IT floor →' }))
  expect(screen.getByRole('button', { name: 'F1 Classroom' })).toBeVisible()
})

test('inventory loads every page and clears old rooms when the edition changes', async () => {
  const editions = ['edition-a', 'edition-b'].map(id => ({ id, seed: 42, config: { weeks: 16 }, generator_version: '1' }))
  const room = (id: string) => ({ id, code: id, kind: 'classroom', capacity: 30, lab_type: null })
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve({
    ok: true, status: 200, json: async () => url.endsWith('/auth/me') ? { id: '1', username: 'viewer', role: 'viewer' } :
      url.endsWith('/datasets') ? { items: editions, total: 2 } :
      url.includes('edition-b') ? { items: [room('B-room')], total: 1 } :
      url.includes('offset=0') ? { items: [room('A-room-1')], total: 2 } : { items: [room('A-room-2')], total: 2 },
  })))
  render(<App/> )
  fireEvent.click(await screen.findByText('Dataset workspace & room inventory'))
  expect(await screen.findByText('A-room-2')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Dataset edition'), { target: { value: 'edition-b' } })
  expect(await screen.findByText('B-room')).toBeVisible()
  expect(screen.queryByText('A-room-1')).not.toBeInTheDocument()
  expect(screen.queryByText('A-room-2')).not.toBeInTheDocument()
})
