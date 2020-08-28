import ccobra
import numpy as np

import spatialreasoner as sr

class SpatialReasoner(ccobra.CCobraModel):
    def __init__(self, name='SpatialReasoner', decide_method='adapted'):
        super(SpatialReasoner, self).__init__(
            name, ['spatial-relational'], ['verify', 'single-choice'])

        # Determine decide method
        if decide_method not in ['skeptical', 'credulous', 'initial', 'adapted']:
            raise ValueError(
                "decide_method not in ['skeptical', 'credulous', 'initial', 'adapted']: {}".format(
                    decide_method))
        self.decide_method = decide_method

        # Initialize spatialreasoner
        ccl = sr.ccl.ClozureCL()
        self.model = sr.spatialreasoner.SpatialReasoner(ccl)

        # Prepare spatialreasoner templates
        self.PREMISE_TEMPLATE = 'the {} is {} the {}'
        self.REL_MAP = {
            'left': 'on the left of',
            'right': 'on the right of',
            'behind': 'behind',
            'front': 'in front of',
            'above': 'above',
            'below': 'below',
            'north': 'north',
            'south': 'south',
            'east': 'east',
            'west': 'west',
            'north-west': 'north-west',
            'north-east': 'north-east',
            'south-west': 'south-west',
            'south-east': 'south-east'
        }

        # Initialize adaption parameters
        self.history = []
        self.last_responses = []
        self.p_indet_true = 0
        self.p_indet_false = 0

    def __deepcopy__(self, memo):
        return SpatialReasoner(self.name, self.decide_method)

    def end_participant(self, identifier, model_log, **kwargs):
        print('end')

        if self.decide_method == 'adapted':
            model_log['p_indet_true'] = self.p_indet_true
            model_log['p_indet_false'] = self.p_indet_false

        self.model.terminate()

    def normalize_task(self, task, choice):
        full_task = task + choice

        # Extract unique terms
        terms = []
        for premise in full_task:
            for term in premise[1:]:
                if term not in terms:
                    terms.append(term)

        # Prepare text replacement dictionary
        replacement_dict = {}
        for idx, term in enumerate(terms):
            replacement_dict[term] = sr.spatialreasoner.TERMS[idx]

        # Prepare normalized problem
        norm_problem = []
        for premise in full_task:
            norm_premise = self.PREMISE_TEMPLATE.format(
                replacement_dict[premise[1]],
                self.REL_MAP[premise[0].lower()],
                replacement_dict[premise[2]]
            )
            norm_problem.append(norm_premise)

        return norm_problem

    def predict(self, item, **kwargs):
        if item.response_type == 'verify':
            norm_problem = self.normalize_task(item.task, item.choices[0])
            sub_predictions = self.model.query(norm_problem)
            self.last_responses = (item.choices[0], sub_predictions)
            prediction = np.all([self.decide(x) for x in sub_predictions])
            return prediction
        elif item.response_type == 'single-choice':
            possible_predictions = []
            for choice in item.choices:
                norm_problem = self.normalize_task(item.task, choice)
                prediction = self.model.query(norm_problem)[0]
                possible_predictions.append((choice, prediction))

            self.last_responses = ([x[0] for x in item.choices], [x[1] for x in possible_predictions])

            decisions = [(x, self.decide(y)) for x, y in possible_predictions]
            pred_filter = [x for x, y in decisions if y]

            if not pred_filter:
                return item.choices[int(np.random.randint(0, len(item.choices)))]
            else:
                return pred_filter[int(np.random.randint(0, len(pred_filter)))]

    def decide(self, prediction):
        if self.decide_method == 'skeptical':
            return self.decide_skeptical(prediction)
        if self.decide_method == 'credulous':
            return self.decide_credulous(prediction)
        if self.decide_method == 'initial':
            return self.decide_initial(prediction)
        if self.decide_method == 'adapted':
            return self.decide_adapted(prediction)
        else:
            raise ValueError('Invalid decide method: {}'.format(prediction))

    def decide_skeptical(self, prediction):
        if prediction == 'true':
            return True
        elif prediction == 'false':
            return False
        elif prediction == 'indeterminate-true':
            return False
        elif prediction == 'indeterminate-false':
            return False
        else:
            raise ValueError('Invalid prediction: {}'.format(prediction))

    def decide_credulous(self, prediction):
        if prediction == 'true':
            return True
        elif prediction == 'false':
            return False
        elif prediction == 'indeterminate-true':
            return True
        elif prediction == 'indeterminate-false':
            return True
        else:
            raise ValueError('Invalid prediction: {}'.format(prediction))

    def decide_initial(self, prediction):
        if prediction == 'true':
            return True
        elif prediction == 'false':
            return False
        elif prediction == 'indeterminate-true':
            return True
        elif prediction == 'indeterminate-false':
            return False
        else:
            raise ValueError('Invalid prediction: {}'.format(prediction))

    def decide_adapted(self, prediction):
        if prediction == 'true':
            return True
        elif prediction == 'false':
            return False
        elif prediction == 'indeterminate-true':
            return self.p_indet_true >= 0
        elif prediction == 'indeterminate-false':
            return self.p_indet_false > 0
        else:
            raise ValueError('Invalid prediction: {}'.format(prediction))

    def pre_train_person(self, dataset):
        if self.decide_method != 'adapted':
            return

        for task_data in dataset:
            self.predict(task_data['item'])
            self.adapt(task_data['item'], task_data['response'])

    def adapt(self, item, truth, **kargs):
        if self.decide_method != 'adapted':
            return

        self.history.append((truth, self.last_responses))

        if item.response_type == 'single-choice':
            best_score = -1
            best_param = None

            for p_indet_true in [-1, 1]:
                for p_indet_false in [-1, 1]:
                    self.p_indet_true = p_indet_true
                    self.p_indet_false = p_indet_false

                    score = 0
                    for target, tuptup in self.history:
                        choices, preds = tuptup

                        decisions = [self.decide(x) for x in preds]
                        true_options = [x for x, y in zip(choices, decisions) if y]

                        if target in true_options:
                            score += 1 / len(true_options)

                    if score > best_score:
                        best_score = score
                        best_param = (p_indet_true, p_indet_false)

            self.p_indet_true = best_param[0]
            self.p_indet_false = best_param[1]
        elif item.response_type == 'verify':
            best_score = -1
            best_param = None

            for p_indet_true in [-1, 1]:
                for p_indet_false in [-1, 1]:
                    self.p_indet_true = p_indet_true
                    self.p_indet_false = p_indet_false

                    score = 0
                    for target, tuptup in self.history:
                        choices, preds = tuptup

                        decisions = [self.decide(x) for x in preds]
                        if target == np.all(decisions):
                            score += 1

                    if score > best_score:
                        best_score = score
                        best_param = (p_indet_true, p_indet_false)

            self.p_indet_true, self.p_indet_false = best_param
