# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 핵심 원칙

- **중요 의사 결정은 반드시 사용자에게 확인** 후 진행한다.
- **모든 동작 수행 후 결과를 검증**하고 검증 결과를 보고한다.
- 응답은 한글(UTF-8)로 진행한다.
- 이모지는 사용하지 않는다.
- 모든 동작 완료후 git commit, push를 진행한다.
- 문장은 짧게 작성한다.
- 고유명사는 영어를 그대로 사용하되, 고유명사가 아닌 것은 한글로 표현해줘.
- 비유는 사용하지마
- ID는 항상 이름을 같이 표기해줘.

## 프로젝트 개요

- 이 레포지토리는 **소프트웨어 구조 설계(Software Architecture Design)** 워크스페이스다.

## 과제 소개

- 구조 설계 워크플로우는 `00_overview.md`(과제 소개)로부터 시작된다.
- 모든 설계 활동의 배경, 목표, 범위, 제약사항은 이 문서를 기준으로 한다.

## 디렉터리 관례

- 각 프로젝트별 설계 산출물은 `프로젝트 이름/docs`의 하위 디렉터리에 저장한다.
- 모든 파일명은 생성 순서를 나타내는 `{nn}_` prefix를 포함한다.
