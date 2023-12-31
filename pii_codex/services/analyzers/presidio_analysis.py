# pylint: disable=broad-except,unused-argument,import-outside-toplevel,unused-variable
from typing import List, Tuple

from ...config import PII_MAPPER, DEFAULT_LANG, DEFAULT_TOKEN_REPLACEMENT_VALUE
from ...models.analysis import DetectionResultItem, DetectionResult
from ...utils.package_installer_util import install_spacy_package
from ...utils.pii_mapping_util import PIIMapper
from ...utils.logging import logger


class PresidioPIIAnalyzer:
    """
    Presidio PII Analyzer - a wrapper for the Microsoft Presidio Analyzer and Anonymization functions
    """

    def __init__(
        self, pii_token_replacement_value: str = DEFAULT_TOKEN_REPLACEMENT_VALUE
    ):
        """
        Since installing Spacy, the en_core_web_lg model, and the MSFT Presidio package are optional installs
        the imports are wrapped to prevent any failures
        @param pii_token_replacement_value: str to replace detected pii token with (e.g. <REDACTED>)
        """

        try:
            import spacy
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            from presidio_anonymizer.entities import OperatorConfig

            if not spacy.util.is_package("en_core_web_lg"):
                # Last resort. Will install the en_core_web_lg package if end-user hadn't already.
                install_spacy_package("en_core_web_lg")

            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self.pii_mapper = PIIMapper()

            self.operators = {
                "DEFAULT": OperatorConfig(
                    "replace", {"new_value": pii_token_replacement_value}
                ),
                "TITLE": OperatorConfig("redact", {}),
            }

        except ImportError:
            raise Exception(
                'Missing dependencies from extras. Install the PII-Codex extras: "detections"'
            )

    def get_supported_entities(self, language_code=DEFAULT_LANG) -> List[str]:
        """
        Retrieves a list of supported entities, this will narrow down what is available for a given language

        @param language_code: str - defaults to "en"
        @return: List[str]
        """
        return self.analyzer.get_supported_entities(language=language_code)  # type: ignore

    def get_loaded_recognizers(self, language_code: str = DEFAULT_LANG):
        """
        Retrieves a list of loaded recognizers, narrowing down the list of what is available for a given language
        @param language_code:
        @return:
        """
        return self.analyzer.get_recognizers(language=language_code)  # type: ignore

    def analyze_item(
        self, text: str, language_code: str = DEFAULT_LANG, entities: List[str] = None
    ) -> Tuple[List[DetectionResultItem], str]:
        """
        Uses Microsoft Presidio (spaCy module) to analyze given a set of entities to analyze the provided text against.
        Will log an error if the identifier or entity recognizer is not added to Presidio's base recognizers or
        a custom recognizer created. Returns the list of detected items and the sanitized string

        @param language_code: str "en" is default
        @param entities: str - List[MSFTPresidioPIIType.name]
        @param text: str
        @return: Tuple[List[DetectionResultItem], str]
        """

        detections = []

        if not entities:
            entities = self.get_supported_entities(language_code)

        try:
            # Engine Setup - spaCy model setup and PII recognizers
            detections = self.analyzer.analyze(  # type: ignore
                text=text, entities=entities, language=language_code
            )

        except Exception as ex:
            logger.error(ex)

        # Return analyzer results in formatted Analysis Result List object
        return [
            DetectionResultItem(
                entity_type=result.entity_type,
                score=result.score,
                start=result.start,
                end=result.end,
            )
            for result in detections
        ], self.sanitize_text(text=text, analysis_items=detections)

    def sanitize_text(
        self, text: str, analysis_items: List[DetectionResultItem]
    ) -> str:
        """
        Sanitizes the text analyzed with MSFT Presidio's Anonymizer
        @param text:
        @param analysis_items:
        @return:
        """
        try:
            anonymization_result = self.anonymizer.anonymize(
                text=text, analyzer_results=analysis_items, operators=self.operators
            )

            return anonymization_result.text

        except Exception as ex:
            logger.error("An error occurred sanitizing the string")
            return ""

    def analyze_collection(
        self, texts: List[str], language_code: str = "en", entities: List[str] = None
    ) -> List[DetectionResult]:
        """
        Uses Microsoft Presidio (spaCy module) to analyze given a set of entities to analyze the provided text against.
        Will log an error if the identifier or entity recognizer is not added to Presidio's base recognizers or
        a custom recognizer created.

        @param language_code: str "en" is default
        @param entities: List[MSFTPresidioPIIType.name] defaults to all possible entities for selected language
        @param texts: List[str]
        @return: List[DetectionResult]
        """

        detection_results = []
        try:
            if not entities:
                entities = self.get_supported_entities(language_code)

            # Engine Setup - spaCy model setup and PII recognizers
            for i, text in enumerate(texts):
                text_analysis = self.analyzer.analyze(  # type: ignore
                    text=text, entities=entities, language=language_code
                )

                # Every analysis by the analyzer will have a set of detections within
                detections = [
                    DetectionResultItem(
                        entity_type=PII_MAPPER.convert_msft_presidio_pii_to_common_pii_type(
                            result.entity_type
                        ).name,
                        score=result.score,
                        start=result.start,
                        end=result.end,
                    )
                    for result in text_analysis
                ]
                detection_results.append(
                    DetectionResult(index=i, detections=detections)
                )

            # Return analyzer results in formatted Analysis Result List object

        except Exception as ex:
            logger.error(ex)

        return detection_results

    @classmethod
    def convert_analyzed_item(cls, pii_detection) -> List[DetectionResultItem]:
        """
        Converts a single Presidio analysis attempt into a collection of DetectionResultItem objects. One string
        analysis by Presidio returns an array of RecognizerResult objects.

        @param pii_detection: RecognizerResult from presidio analyzer
        @return: List[DetectionResultItem]
        """

        return [
            DetectionResultItem(
                entity_type=PII_MAPPER.convert_msft_presidio_pii_to_common_pii_type(
                    result.entity_type
                ).name,
                score=result.score,
                start=result.start,
                end=result.end,
            )
            for result in pii_detection
        ]

    @classmethod
    def convert_analyzed_collection(cls, pii_detections) -> List[DetectionResult]:
        """
        Converts a collection of Presidio analysis results to a collection of DetectionResult. A collection of Presidio
        analysis results ends up being a 2D array.

        @param pii_detections: List[RecognizerResult] from Presidio analyzer
        @return: List[DetectionResult]
        """

        detection_results: List[DetectionResult] = []
        for i, result in enumerate(pii_detections):
            # Return results in formatted Analysis Result List object
            detections = []
            for entity in result:
                detections.append(
                    DetectionResultItem(
                        entity_type=PII_MAPPER.convert_msft_presidio_pii_to_common_pii_type(
                            entity.entity_type
                        ).name,
                        score=entity.score,
                        start=entity.start,
                        end=entity.end,
                    )
                )

            detection_results.append(DetectionResult(index=i, detections=detections))

        return detection_results
