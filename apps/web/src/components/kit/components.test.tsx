import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import {
  Avatar,
  Avatars,
  Btn,
  DayChip,
  DayChips,
  Field,
  Icon,
  LinkBtn,
  SectionTabs,
  SegmentedControl,
  SegItem,
  Sheet,
  SheetBody,
  SheetGrabber,
  StatusStub,
  TabBar,
  TicketStub,
  TripTicket,
  badgeText,
} from './index'

afterEach(cleanup)

const TABS = [
  { key: 'trips', label: 'Trips', icon: 'luggage', href: '/trips' },
  { key: 'discover', label: 'Discover', icon: 'compass', href: '/discover' },
  { key: 'activity', label: 'Activity', icon: 'bell', href: '/activity', badge: 3 },
  { key: 'account', label: 'Account', icon: 'circle-user', href: '/account' },
]

describe('Icon', () => {
  it('draws a sprite symbol with the kit classes', () => {
    const { container } = render(<Icon name="check" size={14} bold className="h-ticket__go" />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('class')).toBe('h-icon h-icon--bold h-ticket__go')
    expect(svg.getAttribute('width')).toBe('14')
    expect(svg.getAttribute('aria-hidden')).toBe('true')
    expect(svg.querySelector('use')!.getAttribute('href')).toBe('#i-check')
  })
})

describe('TabBar', () => {
  it('is nav.h-tabbar named Main with the bar and four items', () => {
    const { container } = render(<TabBar items={TABS} active="trips" />)
    const nav = screen.getByRole('navigation', { name: 'Main' })
    expect(nav.className).toBe('h-tabbar')
    expect(nav.querySelector(':scope > div.h-tabbar__bar')).toBeTruthy()
    const items = container.querySelectorAll('.h-tabbar__bar > a.h-tabbar__item')
    expect(items).toHaveLength(4)
    for (const a of items) {
      expect(a.querySelector(':scope > svg.h-icon')).toBeTruthy()
      expect(a.querySelector(':scope > span')).toBeTruthy()
    }
  })
  it('marks only the active tab with aria-current and the active class', () => {
    const { container } = render(<TabBar items={TABS} active="discover" />)
    const current = container.querySelectorAll('[aria-current="page"]')
    expect(current).toHaveLength(1)
    expect(current[0].className).toBe('h-tabbar__item h-tabbar__item--active')
    expect(current[0].textContent).toBe('Discover')
    expect(container.querySelectorAll('.h-tabbar__item--active')).toHaveLength(1)
  })
  it('gives a badged tab the name "Activity, 3 new" and hides the dot from assistive tech', () => {
    render(<TabBar items={TABS} active="trips" />)
    const link = screen.getByRole('link', { name: 'Activity, 3 new' })
    const badge = link.querySelector('.h-tabbar__badge')!
    expect(badge.textContent).toBe('3')
    expect(badge.getAttribute('aria-hidden')).toBe('true')
    expect(screen.getByRole('link', { name: 'Trips' })).toBeTruthy()
  })
  it('shows 9+ above nine and no badge at zero', () => {
    expect(badgeText(9)).toBe('9')
    expect(badgeText(10)).toBe('9+')
    const items = TABS.map((t) => (t.key === 'activity' ? { ...t, badge: 12 } : { ...t, badge: t.key === 'trips' ? 0 : undefined }))
    const { container } = render(<TabBar items={items} active="trips" />)
    expect(screen.getByRole('link', { name: 'Activity, 12 new' }).querySelector('.h-tabbar__badge')!.textContent).toBe('9+')
    expect(container.querySelectorAll('.h-tabbar__badge')).toHaveLength(1)
  })
})

describe('SectionTabs', () => {
  const items = [
    { key: 'overview', label: 'Overview', href: '/o' },
    { key: 'flights', label: 'Flights', href: '/f' },
  ]
  it('is a named nav of links, the current one aria-current="page"', () => {
    const { container } = render(<SectionTabs items={items} active="flights" label="Trip sections" />)
    const nav = screen.getByRole('navigation', { name: 'Trip sections' })
    expect(nav.className).toBe('h-strip')
    const tabs = container.querySelectorAll('a.h-strip__tab')
    expect(tabs).toHaveLength(2)
    expect(tabs[0].getAttribute('aria-current')).toBeNull()
    expect(tabs[1].getAttribute('aria-current')).toBe('page')
    expect(container.querySelector('[role="tab"]')).toBeNull()
  })
})

describe('SegmentedControl and DayChips', () => {
  it('SegmentedControl is a tablist and SegItem reflects aria-selected', () => {
    render(
      <SegmentedControl narrow aria-label="Stays view">
        <SegItem selected>List</SegItem>
        <SegItem>Compare</SegItem>
      </SegmentedControl>,
    )
    expect(screen.getByRole('tablist', { name: 'Stays view' }).className).toBe('h-seg h-seg--narrow')
    expect(screen.getByRole('tab', { name: 'List' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tab', { name: 'Compare' }).getAttribute('aria-selected')).toBe('false')
    expect(screen.getByRole('tab', { name: 'List' }).className).toBe('h-seg__item')
  })
  it('DayChip marks the selected and current day', () => {
    render(
      <DayChips aria-label="Days">
        <DayChip href="#d1" aria-label="Day 1">D1</DayChip>
        <DayChip href="#d2" aria-label="Day 2" selected current>D2</DayChip>
      </DayChips>,
    )
    expect(screen.getByRole('tablist', { name: 'Days' }).className).toBe('h-daychips')
    const d2 = screen.getByRole('tab', { name: 'Day 2' })
    expect(d2.className).toBe('h-daychip')
    expect(d2.getAttribute('aria-selected')).toBe('true')
    expect(d2.getAttribute('aria-current')).toBe('date')
    expect(screen.getByRole('tab', { name: 'Day 1' }).getAttribute('aria-current')).toBeNull()
  })
})

describe('Avatar', () => {
  it('is an image when named and decorative when not', () => {
    const { container } = render(
      <Avatars>
        <Avatar tone="t1" label="Ana">AN</Avatar>
        <Avatar tone="t2" size="sm">LE</Avatar>
      </Avatars>,
    )
    expect(container.querySelector('.h-avatars')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Ana' }).className).toBe('h-avatar h-avatar--t1')
    const deco = container.querySelector('.h-avatar--sm')!
    expect(deco.className).toBe('h-avatar h-avatar--sm h-avatar--t2')
    expect(deco.getAttribute('aria-hidden')).toBe('true')
  })
})

describe('Btn', () => {
  it('emits the variant and modifier classes', () => {
    render(<Btn variant="secondary" mod={['stub']}>Book</Btn>)
    expect(screen.getByRole('button', { name: 'Book' }).className).toBe('h-btn h-btn--secondary h-btn--stub')
    render(<LinkBtn variant="primary" href="#x">Go</LinkBtn>)
    expect(screen.getByRole('link', { name: 'Go' }).className).toBe('h-btn h-btn--primary')
  })
})

describe('TripTicket', () => {
  it('wraps one card (the element named by `as`) and a stub with the tear', () => {
    const { container } = render(
      <TripTicket as="a" href="#t" aria-label="Costa Rica" mod={['sky']}>
        <div className="h-ticket__body">Body</div>
        <TicketStub>
          <StatusStub status="booked">Booked</StatusStub>
        </TicketStub>
      </TripTicket>,
    )
    const wrap = container.firstElementChild!
    expect(wrap.className).toBe('h-ticket h-ticket--sky')
    const card = screen.getByRole('link', { name: 'Costa Rica' })
    expect(card.className).toBe('h-ticket__card')
    expect(card.parentElement).toBe(wrap)
    const stub = card.querySelector('.h-ticket__stub')!
    expect(stub.firstElementChild!.className).toBe('h-ticket__tear')
    expect(stub.querySelector('.h-stub.h-stub--booked svg.h-icon.h-icon--bold')).toBeTruthy()
  })
  it('leaves the tear out when bare', () => {
    const { container } = render(<TicketStub as="span" bare>x</TicketStub>)
    expect(container.querySelector('.h-ticket__tear')).toBeNull()
    expect(container.firstElementChild!.tagName).toBe('SPAN')
  })
})

describe('Field', () => {
  it('is a label and value pair', () => {
    const { container } = render(<dl><Field label="Nights">11</Field><Field label="Airline" text>TAP</Field></dl>)
    const fields = container.querySelectorAll('.h-field')
    expect(fields[0].className).toBe('h-field')
    expect(fields[1].className).toBe('h-field h-field--text')
    expect(fields[0].querySelector('dt.h-field__label')!.textContent).toBe('Nights')
    expect(fields[0].querySelector('dd.h-field__value')!.textContent).toBe('11')
  })
})

describe('Sheet', () => {
  it('has a grabber and a body', () => {
    const { container } = render(
      <Sheet role="dialog" aria-label="Details">
        <SheetGrabber />
        <SheetBody mod={['roomy']}>x</SheetBody>
      </Sheet>,
    )
    expect(screen.getByRole('dialog', { name: 'Details' }).className).toBe('h-sheet')
    expect(container.querySelector('.h-sheet__grabber')!.getAttribute('aria-hidden')).toBe('true')
    expect(container.querySelector('.h-sheet__body')!.className).toBe('h-sheet__body h-sheet__body--roomy')
  })
})
