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
  expect(await screen.findByText(/No frozen datasets/)).toBeVisible()
  expect(screen.getByText(/Frontend work begins/)).toHaveTextContent('week 4')
})
