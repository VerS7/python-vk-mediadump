.PHONY: stop
stop:
	docker compose down

.PHONY: clean 
clean: stop
	-docker rm vk-mediadump
	-docker rm vk-mediadump
	-docker rmi vk-mediadump
	-docker rmi vk-mediadump

.PHONY: run
run:
	docker compose up -d

.PHONY: build-run
build-run: clean
	docker compose up --build -d