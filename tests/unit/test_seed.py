import random
from datetime import date, timedelta

import seed


def test_seed_reservations_cover_a_year_without_overlaps():
	today = date(2026, 10, 28)
	reservations = seed.build_reservations(random.Random(seed.RANDOM_SEED), today)

	assert min(r['checkin_date'] for r in reservations) >= today - timedelta(days=seed.HISTORY_DAYS)
	assert max(r['checkout_date'] for r in reservations) <= today
	assert len({(r['checkin_date'].year, r['checkin_date'].month) for r in reservations}) >= 12
	assert {r['location'] for r in reservations} == set(seed.LOCATIONS)

	by_room = {}
	for r in reservations:
		by_room.setdefault((r['location'], r['room_number']), []).append(r)
	for stays in by_room.values():
		stays.sort(key=lambda r: r['checkin_date'])
		for previous, current in zip(stays, stays[1:]):
			assert previous['checkout_date'] <= current['checkin_date']


def test_seed_created_at_is_before_checkin_and_never_in_the_future():
	today = date(2026, 10, 28)
	for r in seed.build_reservations(random.Random(seed.RANDOM_SEED), today):
		assert 1 <= (r['checkin_date'] - r['created_at']).days <= 60
		assert r['created_at'] <= today


def test_seed_cards_belong_to_the_reservation_owner():
	reservations = seed.build_reservations(random.Random(seed.RANDOM_SEED), date(2026, 10, 28))
	for r in reservations:
		assert seed.CREDIT_CARDS[r['username']][0] == r['card_number']
